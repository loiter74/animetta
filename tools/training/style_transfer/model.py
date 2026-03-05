"""
风格转换模型模块
PyTorch Lightning Module for Style Transfer with LoRA
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass

import torch
import torch.nn as nn
from torch.optim import AdamW
from torch.utils.data import DataLoader

import pytorch_lightning as pl
from pytorch_lightning.utilities import grad_norm

from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    PreTrainedModel,
    get_linear_schedule_with_warmup,
)
from peft import (
    LoraConfig,
    get_peft_model,
    TaskType,
    PeftModel,
)

from .config import StyleTransferConfig, LoRAConfig


class StyleTransferModule(pl.LightningModule):
    """
    风格转换 Lightning Module

    使用 Qwen2.5-7B-Instruct + LoRA 进行风格转换微调
    """

    def __init__(
        self,
        config: StyleTransferConfig,
        tokenizer: Optional[AutoTokenizer] = None,
    ):
        super().__init__()

        self.config = config
        self.save_hyperparameters(config.__dict__)

        # 模型和tokenizer会延迟加载
        self.model = None
        self.tokenizer = tokenizer
        self.lora_config = None

    def setup(self, stage: Optional[str] = None) -> None:
        """初始化模型和tokenizer"""
        if self.model is not None:
            return  # 已经初始化

        # 加载 tokenizer
        if self.tokenizer is None:
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.config.model.base_model,
                cache_dir=self.config.model.cache_dir,
                trust_remote_code=True,
                use_fast=self.config.model.use_flash_attention,
            )

        # 确保有 pad_token_id
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = "<|endoftext|>"

        # 加载基础模型
        base_model = AutoModelForCausalLM.from_pretrained(
            self.config.model.base_model,
            cache_dir=self.config.model.cache_dir,
            torch_dtype=torch.bfloat16 if "bf16" in self.config.training.precision else torch.float32,
            trust_remote_code=True,
            use_flash_attention_2=self.config.model.use_flash_attention,
        )

        # 配置 LoRA
        lora_cfg = LoraConfig(
            task_type=TaskType.CAUSAL_LM,
            r=self.config.lora.r,
            lora_alpha=self.config.lora.lora_alpha,
            lora_dropout=self.config.lora.lora_dropout,
            target_modules=self.config.lora.target_modules,
            bias=self.config.lora.bias,
        )

        # 应用 LoRA
        self.model = get_peft_model(base_model, lora_cfg)
        self.lora_config = lora_cfg

        # 打印可训练参数
        trainable_params = sum(p.numel() for p in self.model.parameters() if p.requires_grad)
        all_params = sum(p.numel() for p in self.model.parameters())
        print(f"Trainable parameters: {trainable_params:,} / {all_params:,} ({100*trainable_params/all_params:.2f}%)")

        # 启用 gradient checkpointing
        if self.config.training.gradient_checkpointing:
            self.model.gradient_checkpointing_enable()

    def forward(self, batch: Dict[str, torch.Tensor]) -> Dict[str, torch.Tensor]:
        """
        娡型前向传播

        Args:
            batch: 包含 input_ids, attention_mask. labels 的字典

        Returns:
            包含 loss. logits 等的字典
        """
        outputs = self.model(
            input_ids=batch["input_ids"],
            attention_mask=batch["attention_mask"],
            labels=batch["labels"],
        )

        return {
            "loss": outputs.loss,
            "logits": outputs.logits,
        }

    def training_step(self, batch: Dict[str, torch.Tensor], batch_idx: int) -> torch.Tensor:
        """训练步骤"""
        outputs = self.forward(batch)
        loss = outputs["loss"]

        # 记录指标
        self.log_dict({
            "train_loss": loss,
            "learning_rate": self.trainer.optimizers[0].param_groups[0]["lr"],
        })

        return loss

    def validation_step(self, batch: Dict[str, torch.Tensor], batch_idx: int) -> torch.Tensor:
        """验证步骤"""
        outputs = self.forward(batch)
        loss = outputs["loss"]

        self.log_dict({"val_loss": loss})

        return loss

    def configure_optimizers(self) -> List[torch.optim.Optimizer]:
        """配置优化器"""
        no_decay = ["bias", "LayerNorm.weight", "LayerNorm.bias"]
        optimizer_grouped_parameters = []

        for name, param in self.model.named_parameters():
            if not param.requires_grad:
                continue

            if any(nd in name for nd in no_decay):
                optimizer_grouped_parameters.append({
                    "params": [param],
                    "weight_decay": 0.0,
                })
            else:
                optimizer_grouped_parameters.append({
                    "params": [param],
                    "weight_decay": self.config.training.weight_decay,
                })

        optimizer = AdamW(
            optimizer_grouped_parameters,
            lr=self.config.training.learning_rate,
            betas=(0.9, 0.999),
        )

        return [optimizer]

    def configure_lr_scheduler(
        self,
        optimizer: torch.optim.Optimizer,
    ) -> Any:
        """配置学习率调度器"""
        num_training_steps = self.trainer.estimated_stepping_batches

        scheduler = get_linear_schedule_with_warmup(
            optimizer,
            num_warmup_steps=int(num_training_steps * self.config.training.warmup_ratio),
            num_training_steps=num_training_steps,
        )

        return {
            "scheduler": scheduler,
            "interval": 1,
        }

    def on_train_batch_start(self, batch: Any, batch_idx: int) -> None:
        """每个batch开始时的回调"""
        pass

    def on_train_epoch_start(self) -> None:
        """每个epoch开始时的回调"""
        pass

    def on_validation_epoch_start(self) -> None:
        """验证epoch开始时的回调"""
        pass

    def on_train_epoch_end(self) -> None:
        """每个epoch结束时的回调"""
        pass

    def on_validation_epoch_end(self) -> None:
        """验证epoch结束时的回调"""
        pass

    def save_model(self, output_dir: str) -> None:
        """保存模型"""
        import os
        output_path = os.path.join(output_dir, "lora_adapter")
        self.model.save_pretrained(output_path)

        # 同时保存 tokenizer
        self.tokenizer.save_pretrained(output_path)

        print(f"Model saved to {output_path}")

    def load_model(self, model_path: str) -> None:
        """加载已训练的模型"""
        from peft import PeftModel

        # 加载基础模型
        base_model = AutoModelForCausalLM.from_pretrained(
            self.config.model.base_model,
            cache_dir=self.config.model.cache_dir,
            torch_dtype=torch.bfloat16,
        )

        # 加载 LoRA 适配器
        self.model = PeftModel.from_pretrained(base_model, model_path)
        print(f"Model loaded from {model_path}")

    def generate(
        self,
        input_text: str,
        max_new_tokens: int = 256,
        temperature: float = 0.7,
        top_p: float = 0.9,
        do_sample: bool = True,
    ) -> str:
        """
        生成目标风格文本

        Args:
            input_text: 中性输入文本
            max_new_tokens: 最大生成token数
            temperature: 采样温度
            top_p: top-p 采样
            do_sample: 是否采样

        Returns:
            生成的目标风格文本
        """
        self.model.eval()

        # 构建 prompt
        prompt = self._build_inference_prompt(input_text)
        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.device)

        # 生成
        with torch.no_grad():
            outputs = self.model.generate(
                input_ids=inputs["input_ids"],
                attention_mask=inputs["attention_mask"],
                max_new_tokens=max_new_tokens,
                temperature=temperature,
                top_p=top_p,
                do_sample=do_sample,
                pad_token_id=self.tokenizer.pad_token_id,
                eos_token_id=self.tokenizer.eos_token_id,
            )

        # 解码
        generated_text = self.tokenizer.decode(
            outputs[0],
            skip_special_tokens=True,
        )

        return generated_text

    def _build_inference_prompt(self, source_text: str) -> str:
        """构建推理时的 prompt"""
        system_prompt = f"你是一个风格转换助手。请将输入的文本转换为{self.config.style_name}风格。\\n风格描述: {self.config.style_description}"
        if self.config.style_description else ""}"

        if hasattr(self.tokenizer, "apply_chat_template"):
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"将以下文本转换风格:\n{source_text}"},
            ]
            return self.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        else:
            # Fallback for tokenizers without chat template
            return f"<|im_start|>system\n{system_prompt}<|im_end|>\n<|im_start|>user\n将以下文本转换风格:\n{source_text}<|im_end|>\n<|im_start|>assistant\n"
