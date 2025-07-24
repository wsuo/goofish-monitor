import os
import sys
import argparse
import asyncio
import json
import aiofiles
import aiohttp
from dotenv import load_dotenv
from openai import AsyncOpenAI

# --- AI Configuration ---
load_dotenv()
API_KEY = os.getenv("OPENAI_API_KEY")
BASE_URL = os.getenv("OPENAI_BASE_URL")
MODEL_NAME = os.getenv("OPENAI_MODEL_NAME")

# Check configuration
if not all([BASE_URL, MODEL_NAME]):
    raise ValueError("错误：请确保在 .env 文件中完整设置了 OPENAI_BASE_URL 和 OPENAI_MODEL_NAME。(OPENAI_API_KEY 对于某些服务是可选的)")

# 判断是否使用 Gemini API
USE_GEMINI_API = "generativelanguage.googleapis.com" in BASE_URL

if USE_GEMINI_API:
    print("检测到 Gemini API 配置，使用 Gemini 兼容模式")
    client = None
else:
    # Initialize OpenAI client
    try:
        client = AsyncOpenAI(
            api_key=API_KEY, 
            base_url=BASE_URL,
            timeout=60.0  # 设置60秒超时，适合prompt生成任务
        )
    except Exception as e:
        raise RuntimeError(f"初始化 OpenAI 客户端时出错: {e}") from e

async def call_gemini_api_prompt(contents):
    """为 prompt_generator 调用 Gemini API 的函数"""
    url = f"{BASE_URL}/models/{MODEL_NAME}:generateContent"
    
    headers = {
        'Content-Type': 'application/json',
        'X-goog-api-key': API_KEY
    }
    
    payload = {
        "contents": contents
    }
    
    timeout = aiohttp.ClientTimeout(total=60)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.post(url, headers=headers, json=payload) as response:
            if response.status != 200:
                error_text = await response.text()
                raise aiohttp.ClientResponseError(
                    request_info=response.request_info,
                    history=response.history,
                    status=response.status,
                    message=f"Gemini API 错误: {error_text}"
                )
            
            result = await response.json()
            return result

# The meta-prompt to instruct the AI
META_PROMPT_TEMPLATE = """
你是一位世界级的AI提示词工程大师。你的任务是根据用户提供的【购买需求】，模仿一个【参考范例】，为闲鱼监控机器人的AI分析模块（代号 EagleEye）生成一份全新的【分析标准】文本。

你的输出必须严格遵循【参考范例】的结构、语气和核心原则，但内容要完全针对用户的【购买需求】进行定制。最终生成的文本将作为AI分析模块的思考指南。

---
这是【参考范例】（`macbook_criteria.txt`）：
```text
{reference_text}
```
---

这是用户的【购买需求】：
```text
{user_description}
```
---

请现在开始生成全新的【分析标准】文本。请注意：
1.  **只输出新生成的文本内容**，不要包含任何额外的解释、标题或代码块标记。
2.  保留范例中的 `[V6.3 核心升级]`、`[V6.4 逻辑修正]` 等版本标记，这有助于保持格式一致性。
3.  将范例中所有与 "MacBook" 相关的内容，替换为与用户需求商品相关的内容。
4.  思考并生成针对新商品类型的“一票否决硬性原则”和“危险信号清单”。
"""

async def generate_criteria(user_description: str, reference_file_path: str) -> str:
    """
    Generates a new criteria file content using AI.
    """
    print(f"正在读取参考文件: {reference_file_path}")
    try:
        with open(reference_file_path, 'r', encoding='utf-8') as f:
            reference_text = f.read()
    except FileNotFoundError:
        raise FileNotFoundError(f"参考文件未找到: {reference_file_path}")
    except IOError as e:
        raise IOError(f"读取参考文件失败: {e}")

    print("正在构建发送给AI的指令...")
    prompt = META_PROMPT_TEMPLATE.format(
        reference_text=reference_text,
        user_description=user_description
    )

    print("正在调用AI生成新的分析标准，请稍候...")
    try:
        if USE_GEMINI_API:
            # 使用 Gemini API
            contents = [{"parts": [{"text": prompt}]}]
            response = await call_gemini_api_prompt(contents)
            
            # 解析 Gemini 响应
            if "candidates" in response and len(response["candidates"]) > 0:
                candidate = response["candidates"][0]
                if "content" in candidate and "parts" in candidate["content"]:
                    generated_text = candidate["content"]["parts"][0]["text"]
                else:
                    raise ValueError("Gemini API 响应格式错误：未找到内容")
            else:
                raise ValueError("Gemini API 响应格式错误：未找到候选结果")
        else:
            # 使用 OpenAI API
            response = await client.chat.completions.create(
                model=MODEL_NAME,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.5, # Lower temperature for more predictable structure
            )
            generated_text = response.choices[0].message.content
            
        print("AI已成功生成内容。")
        return generated_text.strip()
    except Exception as e:
        print(f"调用 AI API 时出错: {e}")
        raise e


async def update_config_with_new_task(new_task: dict, config_file: str = "config.json"):
    """
    将一个新任务添加到指定的JSON配置文件中。
    """
    print(f"正在更新配置文件: {config_file}")
    try:
        # 读取现有配置
        config_data = []
        if os.path.exists(config_file):
            async with aiofiles.open(config_file, 'r', encoding='utf-8') as f:
                content = await f.read()
                # 处理空文件的情况
                if content.strip():
                    config_data = json.loads(content)

        # 追加新任务
        config_data.append(new_task)

        # 写回配置文件
        async with aiofiles.open(config_file, 'w', encoding='utf-8') as f:
            await f.write(json.dumps(config_data, ensure_ascii=False, indent=2))
        
        print(f"成功！新任务 '{new_task.get('task_name')}' 已添加到 {config_file} 并已启用。")
        return True
    except json.JSONDecodeError:
        sys.stderr.write(f"错误: 配置文件 {config_file} 格式错误，无法解析。\n")
        return False
    except IOError as e:
        sys.stderr.write(f"错误: 读写配置文件失败: {e}\n")
        return False


async def main():
    parser = argparse.ArgumentParser(
        description="使用AI根据用户需求和参考范例，生成闲鱼监控机器人的分析标准文件，并自动更新config.json。",
        epilog="""
使用示例:
  python prompt_generator.py \\
    --description "我想买一台95新以上的索尼A7M4相机，预算在10000到13000元之间..." \\
    --output prompts/sony_a7m4_criteria.txt \\
    --task-name "Sony A7M4" \\
    --keyword "a7m4" \\
    --min-price "10000" \\
    --max-price "13000"
""",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--description", type=str, required=True, help="你详细的购买需求描述。")
    parser.add_argument("--output", type=str, required=True, help="新生成的分析标准文件的保存路径。")
    parser.add_argument("--reference", type=str, default="prompts/macbook_criteria.txt", help="作为模仿范例的参考文件路径。")
    # New arguments for config.json
    parser.add_argument("--task-name", type=str, required=True, help="新任务的名称 (例如: 'Sony A7M4')。")
    parser.add_argument("--keyword", type=str, required=True, help="新任务的搜索关键词 (例如: 'a7m4')。")
    parser.add_argument("--min-price", type=str, help="最低价格。")
    parser.add_argument("--max-price", type=str, help="最高价格。")
    parser.add_argument("--max-pages", type=int, default=3, help="最大搜索页数 (默认: 3)。")
    parser.add_argument('--no-personal-only', dest='personal_only', action='store_false', help="如果设置，则不筛选个人卖家。")
    parser.set_defaults(personal_only=True)
    parser.add_argument("--config-file", type=str, default="config.json", help="任务配置文件的路径 (默认: config.json)。")
    args = parser.parse_args()

    # Ensure the output directory exists
    output_dir = os.path.dirname(args.output)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    generated_criteria = await generate_criteria(args.description, args.reference)

    if generated_criteria:
        try:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(generated_criteria)
            print(f"\n成功！新的分析标准已保存到: {args.output}")
        except IOError as e:
            sys.exit(f"错误: 写入输出文件失败: {e}")

        # 创建新任务条目
        new_task = {
            "task_name": args.task_name,
            "enabled": True,
            "keyword": args.keyword,
            "max_pages": args.max_pages,
            "personal_only": args.personal_only,
            "ai_prompt_base_file": "prompts/base_prompt.txt",
            "ai_prompt_criteria_file": args.output
        }
        if args.min_price:
            new_task["min_price"] = args.min_price
        if args.max_price:
            new_task["max_price"] = args.max_price

        # 使用重构的函数更新 config.json
        success = await update_config_with_new_task(new_task, args.config_file)
        if success:
            print("现在，你可以直接运行 `python spider_v2.py` 来启动包括新任务在内的所有监控。")

if __name__ == "__main__":
    asyncio.run(main())
