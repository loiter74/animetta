"""
风格转换训练入口
Style Transfer Training Entry Point
"""

import argparse
from pathlib import Path

import torch
import pytorch_lightning as pl
from pytorch_lightning.callbacks import ModelCheckpoint, EarlyStopping, LearningRateMonitor
from pytorch_lightning.loggers import TensorBoardLogger

from loguru import logger

from .config import StyleTransferConfig
from .data_module import StyleTransferDataModule
from .model import StyleTransferModule


def parse_args():
    parser = argparse.ArgumentParser(description="风格转换训练")
    parser.add_argument("--config", "-c", type=str,
                        default="tools/training/configs/style_transfer.yaml",
                        help="配置文件路径")
    parser.add_argument("--output-dir", "-o", type=str, default=None,
                        help="输出目录 (覆盖配置文件)")
    parser.add_argument("--resume", "-r", type=str, default=None,
                        help="从checkpoint恢复训练")
    parser.add_argument("--gpus", "-g", type=int, default=1,
                        help="GPU数量")
    parser.add_argument("--precision", "-p", type=str, default="bf16-mixed",
                        choices=["fp16", "bf16-mixed", "32"],
                        help="训练精度")
    parser.add_argument("--style-name", "-s", type=str, default=None,
                        help="风格名称")
    parser.add_argument("--style-desc", type=str, default=None,
                        help="风格描述")
    return parser.parse_args()


def setup_callbacks(config: StyleTransferConfig, output_dir: Path):
    """设置回调函数"""
    callbacks = []

    # ModelCheckpoint - 保存最佳模型
    checkpoint_callback = ModelCheckpoint(
        dirpath=output_dir / "checkpoints",
        filename="style_transfer-{epoch:02d}-{val_loss:.4f}",
        monitor="val_loss",
        mode="min",
        save_top_k=3,
        save_last=True,
        every_n_epochs=1,
        verbose=True,
    )
    callbacks.append(checkpoint_callback)

    # EarlyStopping - 早停
    early_stop_callback = EarlyStopping(
        monitor="val_loss",
        min_delta=0.001,
        patience=5,
        mode="min",
        verbose=True,
    )
    callbacks.append(early_stop_callback)

    # LearningRateMonitor - 学习率监控
    lr_monitor = LearningRateMonitor(logging_interval="step")
    callbacks.append(lr_monitor)

    return callbacks


def setup_loggers(config: StyleTransferConfig, output_dir: Path):
    """设置日志记录器"""
    loggers = []

    # TensorBoard
    tb_logger = TensorBoardLogger(
        save_dir=output_dir / "logs",
        name="style_transfer",
    )
    loggers.append(tb_logger)

    return loggers


def main():
    args = parse_args()

    # 加载配置
    config_path = Path(args.config)
    if config_path.exists():
        config = StyleTransferConfig.from_yaml(str(config_path))
        logger.info(f"Loaded config from {config_path}")
    else:
        logger.warning(f"Config file not found: {config_path}, using default config")
        config = StyleTransferConfig()

    # 覆盖配置
    if args.output_dir:
        config.output_dir = args.output_dir
    if args.precision:
        config.training.precision = args.precision
    if args.style_name:
        config.style_name = args.style_name
    if args.style_desc:
        config.style_description = args.style_desc

    # 设置输出目录
    output_dir = Path(config.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # 保存配置
    config.to_yaml(output_dir / "config.yaml")

    # 设置随机种子
    pl.seed_everything(config.seed)

    # 打印配置信息
    logger.info("=" * 50)
    logger.info("Style Transfer Training Configuration")
    logger.info("=" * 50)
    logger.info(f"Output directory: {output_dir}")
    logger.info(f"Base model: {config.model.base_model}")
    logger.info(f"Style name: {config.style_name}")
    logger.info(f"LoRA rank: {config.lora.r}")
    logger.info(f"Learning rate: {config.training.learning_rate}")
    logger.info(f"Batch size: {config.training.batch_size}")
    logger.info(f"Max epochs: {config.training.max_epochs}")
    logger.info(f"Precision: {config.training.precision}")
    logger.info(f"Data root: {config.data.data_root}")
    logger.info("=" * 50)

    # 初始化数据模块
    data_module = StyleTransferDataModule(config=config)

    # 初始化模型
    model = StyleTransferModule(config=config)

    # 设置回调
    callbacks = setup_callbacks(config, output_dir)
    loggers = setup_loggers(config, output_dir)

    # 初始化 Trainer
    trainer = pl.Trainer(
        max_epochs=config.training.max_epochs,
        accelerator="gpu",
        devices=args.gpus,
        precision=config.training.precision,
        gradient_clip_val=1.0,
        accumulate_grad_batches=config.training.gradient_accumulation_steps,
        log_every_n_steps=config.training.log_every_n_steps,
        val_check_interval=config.training.val_check_interval,
        callbacks=callbacks,
        logger=loggers,
        enable_progress_bar=True,
        deterministic="warn",
    )

    # 开始训练
    logger.info("Starting training...")
    trainer.fit(
        model,
        data_module,
        ckpt_path=args.resume,
    )

    # 训练完成
    logger.info("Training completed!")

    # 保存最终模型
    final_output_dir = output_dir / "final"
    final_output_dir.mkdir(parents=True, exist_ok=True)

    # 保存 LoRA 权重
    model.model.save_pretrained(final_output_dir / "lora")
    logger.info(f"LoRA weights saved to {final_output_dir / 'lora'}")

    # 保存 tokenizer
    data_module.tokenizer.save_pretrained(final_output_dir)
    logger.info(f"Tokenizer saved to {final_output_dir}")

    # 测试生成
    logger.info("Testing generation...")
    test_prompts = [
        "你好，请问你是谁？有什么可以帮助你的吗?",
        "今天天气真好。",
        "我有一个问题想请教你。",
    ]

    for prompt in test_prompts:
        generated = model.generate(prompt, max_new_tokens=100)
        logger.info(f"Input: {prompt}")
        logger.info(f"Output: {generated}")
        logger.info("-" * 40)


if __name__ == "__main__":
    main()
