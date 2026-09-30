#!/usr/bin/env python3
"""
豆芽AI诊所 — 医疗大模型微调脚本
===============================
使用 HuggingFace Transformers + QLoRA 对医疗诊断数据进行微调。

依赖安装:
    pip install torch transformers datasets peft accelerate bitsandbytes
    pip install trl  # 用于 Supervised Fine-Tuning

使用方法:
    python fine_tune.py --data_file medical_training_data.jsonl --output_dir ./medical_adapter

如果需要使用更多样本进行微调，可以自行在 medical_training_data.jsonl 中添加更多数据。
"""

import argparse
import json
import logging
import os
import sys
from typing import Dict, List

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def load_jsonl_data(data_path: str) -> List[Dict]:
    """加载 JSONL 格式的训练数据"""
    if not os.path.exists(data_path):
        logger.error(f"数据文件不存在: {data_path}")
        sys.exit(1)

    data = []
    with open(data_path, "r", encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
                if "messages" in record and len(record["messages"]) == 3:
                    data.append(record)
                else:
                    logger.warning(f"第 {i} 行格式不正确（需要3条messages），跳过")
            except json.JSONDecodeError as e:
                logger.warning(f"第 {i} 行JSON解析失败: {e}，跳过")

    logger.info(f"成功加载 {len(data)} 条训练样本")
    return data


def format_chat_template(record: Dict) -> str:
    """将 OpenAI 格式的消息转为聊天模板格式"""
    messages = record["messages"]
    system_msg = messages[0]["content"]
    user_msg = messages[1]["content"]
    assistant_msg = messages[2]["content"]

    # 构建对话模板
    text = f"<|system|>\n{system_msg}\n</s>\n"
    text += f"<|user|>\n{user_msg}\n</s>\n"
    text += f"<|assistant|>\n{assistant_msg}\n</s>"
    return text


def format_alpaca(record: Dict) -> str:
    """将格式转为 Alpaca 指令格式"""
    messages = record["messages"]
    system_msg = messages[0]["content"]
    user_msg = messages[1]["content"]
    assistant_msg = messages[2]["content"]

    return (
        f"Below is an instruction that describes a task, paired with an input that provides further context.\n"
        f"Write a response that appropriately completes the request.\n\n"
        f"### Instruction:\n{system_msg}\n\n"
        f"### Input:\n{user_msg}\n\n"
        f"### Response:\n{assistant_msg}"
    )


def main():
    parser = argparse.ArgumentParser(description="AI医疗大模型微调脚本")
    parser.add_argument("--data_file", type=str, default="medical_training_data.jsonl",
                        help="训练数据 JSONL 文件路径")
    parser.add_argument("--output_dir", type=str, default="./medical_adapter",
                        help="微调后的适配器权重保存路径")
    parser.add_argument("--base_model", type=str, default="Qwen/Qwen2.5-7B-Instruct",
                        help="基础模型名称或路径（默认使用Qwen2.5-7B）")
    parser.add_argument("--template", type=str, default="chat",
                        choices=["chat", "alpaca"],
                        help="对话模板格式")
    parser.add_argument("--epochs", type=int, default=3,
                        help="训练轮数")
    parser.add_argument("--batch_size", type=int, default=4,
                        help="训练批大小（per_device）")
    parser.add_argument("--lr", type=float, default=2e-4,
                        help="学习率")
    parser.add_argument("--lora_r", type=int, default=16,
                        help="LoRA rank")
    parser.add_argument("--lora_alpha", type=float, default=32,
                        help="LoRA alpha")
    parser.add_argument("--check_only", action="store_true",
                        help="仅检查数据格式，不执行微调")
    args = parser.parse_args()

    # 1. 加载数据
    logger.info(f"加载训练数据: {args.data_file}")
    raw_data = load_jsonl_data(args.data_file)

    if len(raw_data) == 0:
        logger.error("没有有效的训练数据，退出")
        sys.exit(1)

    if args.check_only:
        logger.info(f"数据检查完成：共 {len(raw_data)} 条有效样本")
        logger.info("示例数据格式：")
        print(raw_data[0]["messages"][0]["content"][:80] + "...")
        logger.info("格式正确，可以开始微调。使用方法：")
        print(f"  python {sys.argv[0]} --data_file {args.data_file}")
        return

    # 2. 格式化数据
    logger.info("格式化训练数据...")
    formatter = format_chat_template if args.template == "chat" else format_alpaca
    texts = [formatter(record) for record in raw_data]

    logger.info(f"示例格式化文本 (前200字符):")
    logger.info(texts[0][:200])

    # ============================================================
    # 以下代码在实际微调时需要取消注释，并确保安装所有依赖
    # ============================================================
    """
    # 3. 加载模型和分词器
    from transformers import (
        AutoModelForCausalLM,
        AutoTokenizer,
        TrainingArguments,
        BitsAndBytesConfig,
    )
    from peft import (
        LoraConfig,
        get_peft_model,
        prepare_model_for_kbit_training,
        TaskType,
    )
    from datasets import Dataset
    from trl import SFTTrainer

    logger.info(f"加载基础模型: {args.base_model}")

    # QLoRA 量化配置 (4-bit)
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_use_double_quant=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
    )

    # 加载模型 (带量化)
    model = AutoModelForCausalLM.from_pretrained(
        args.base_model,
        quantization_config=bnb_config,
        device_map="auto",
        trust_remote_code=True,
        torch_dtype=torch.bfloat16,
    )
    model.config.use_cache = False
    model = prepare_model_for_kbit_training(model)

    # 加载分词器
    tokenizer = AutoTokenizer.from_pretrained(
        args.base_model,
        trust_remote_code=True,
        padding_side="right",
    )
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    # LoRA 配置
    peft_config = LoraConfig(
        r=args.lora_r,
        lora_alpha=args.lora_alpha,
        lora_dropout=0.05,
        bias="none",
        task_type=TaskType.CAUSAL_LM,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                        "gate_proj", "up_proj", "down_proj"],
    )
    model = get_peft_model(model, peft_config)
    model.print_trainable_parameters()

    # 创建 Dataset
    dataset = Dataset.from_list([{"text": t} for t in texts])

    # 训练参数
    training_args = TrainingArguments(
        output_dir=args.output_dir,
        per_device_train_batch_size=args.batch_size,
        gradient_accumulation_steps=4,
        num_train_epochs=args.epochs,
        learning_rate=args.lr,
        bf16=True,
        logging_steps=10,
        save_steps=50,
        save_total_limit=2,
        remove_unused_columns=False,
        report_to="none",
    )

    # SFT Trainer
    trainer = SFTTrainer(
        model=model,
        args=training_args,
        train_dataset=dataset,
        tokenizer=tokenizer,
        dataset_text_field="text",
        max_seq_length=2048,
    )

    # 开始训练
    logger.info("开始微调训练...")
    trainer.train()

    # 保存模型
    logger.info(f"保存微调后的适配器到: {args.output_dir}")
    trainer.save_model(args.output_dir)
    tokenizer.save_pretrained(args.output_dir)

    logger.info("微调完成！")
    """

    # 数据检查模式下的提示
    if len(raw_data) < 30:
        logger.warning(f"当前只有 {len(raw_data)} 条样本，建议至少 100+ 条以获得更好的微调效果")
    else:
        logger.info(f"共 {len(raw_data)} 条训练样本，微调所需的最小数据量已满足")

    logger.info(f"微调适配器将保存到: {args.output_dir}")

    # 提供推理示例代码
    print("\n" + "=" * 60)
    print("  微调后推理示例代码")
    print("=" * 60)
    print("""
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch

# 加载基础模型
base_model = AutoModelForCausalLM.from_pretrained(
    "Qwen/Qwen2.5-7B-Instruct",
    torch_dtype=torch.bfloat16,
    device_map="auto",
)
tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen2.5-7B-Instruct", trust_remote_code=True)

# 加载微调的 LoRA 适配器
model = PeftModel.from_pretrained(base_model, "./medical_adapter")
model.eval()

# 推理
def medical_diagnosis(symptoms_text):
    system_prompt = "你是豆芽诊所的一名资深全科医生，名叫"豆芽医生"。..."
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": symptoms_text},
    ]
    text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer(text, return_tensors="pt").to(model.device)
    outputs = model.generate(
        **inputs,
        max_new_tokens=2048,
        temperature=0.3,
        do_sample=True,
    )
    response = tokenizer.decode(outputs[0], skip_special_tokens=True)
    # 解析 response 中的 JSON 部分
    return response

# 测试
result = medical_diagnosis("【患者信息】\\n姓名：测试患者\\n年龄：35岁\\n性别：男\\n【症状描述】发烧38.5度，咳嗽有痰")
print(result)
""")


if __name__ == "__main__":
    main()
