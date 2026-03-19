#!/usr/bin/env python3
"""
表情稳定性自动化测试脚本

测试表情系统的稳定性，检测：
1. audio_with_expression 事件是否到达
2. 期望的表情是否正确
3. idle 是否过早覆盖表情
"""

import socketio
import time
import json
import asyncio
from typing import List, Dict, Any
from dataclasses import dataclass
from datetime import datetime


@dataclass
class TestCase:
    """测试用例"""
    input: str
    expected_emotion: str = None
    description: str = ""


@dataclass
class TestResult:
    """测试结果"""
    case: str
    status: str  # PASS, FAIL
    detail: str
    events_received: int
    has_audio: bool
    emotion_match: bool
    idle_too_early: bool


class StabilityTester:
    """表情稳定性测试器"""

    # 测试用例
    TEST_CASES = [
        TestCase(input="做个悲伤的表情", expected_emotion="sad", description="悲伤表情"),
        TestCase(input="做个开心的表情", expected_emotion="happy", description="开心表情"),
        TestCase(input="做个震惊的表情", expected_emotion="surprised", description="惊讶表情"),
        TestCase(input="你在想什么", expected_emotion="thinking", description="思考表情"),
        TestCase(input="你好呀", expected_emotion=None, description="普通对话"),
    ]

    def __init__(self, url="http://localhost:12394"):
        """
        初始化测试器

        Args:
            url: Socket.IO 服务器地址
        """
        self.url = url
        self.sio = None
        self.results = []
        self.current_events = []
        self.round_num = 0

    async def connect(self):
        """连接到服务器"""
        self.sio = socketio.AsyncClient()

        @self.sio.on('connect')
        def on_connect():
            print(f"✅ 已连接到 {self.url}")

        @self.sio.on('disconnect')
        def on_disconnect():
            print("❌ 已断开连接")

        @self.sio.on('expression')
        def on_expression(data):
            self.current_events.append({
                'type': 'expression',
                'value': data.get('expression') if isinstance(data, dict) else data,
                'time': time.time()
            })

        @self.sio.on('audio_with_expression')
        def on_audio(data):
            emotions = []
            if isinstance(data, dict):
                if 'expressions' in data:
                    expr = data['expressions']
                    if isinstance(expr, dict) and 'segments' in expr:
                        emotions = [s.get('emotion') for s in expr['segments']]
                    elif isinstance(expr, dict) and 'frames' in expr:
                        # 参数映射模式
                        emotions = ['<param_mapped>']

            self.current_events.append({
                'type': 'audio_with_expression',
                'emotions': emotions,
                'time': time.time()
            })

        @self.sio.on('text')
        def on_text(data):
            self.current_events.append({
                'type': 'text',
                'value': data.get('text', ''),
                'time': time.time()
            })

        await self.sio.connect(self.url)

    async def disconnect(self):
        """断开连接"""
        if self.sio:
            await self.sio.disconnect()

    async def send_text(self, text: str, from_name: str = "Tester"):
        """发送文本输入"""
        await self.sio.emit('text_input', {
            'text': text,
            'from_name': from_name
        })

    async def wait_for_completion(self, timeout: float = 10.0):
        """
        等待当前交互完成

        Args:
            timeout: 超时时间（秒）
        """
        await asyncio.sleep(timeout)

    def _analyze(self, case: TestCase, events: List[Dict]) -> TestResult:
        """
        分析测试结果

        Args:
            case: 测试用例
            events: 接收到的事件列表

        Returns:
            TestResult: 测试结果
        """
        types = [e['type'] for e in events]

        # 检查 1: audio 事件是否到达
        has_audio = 'audio_with_expression' in types

        # 检查 2: 期望的表情是否出现
        emotions_received = []
        for e in events:
            if e['type'] == 'audio_with_expression':
                emotions_received.extend(e.get('emotions', []))

        if case.expected_emotion is None:
            emotion_match = True
        else:
            emotion_match = case.expected_emotion in emotions_received

        # 检查 3: idle 是否过早覆盖
        idle_too_early = False
        for i, e in enumerate(events):
            if e['type'] == 'audio_with_expression' and i + 1 < len(events):
                next_e = events[i + 1]
                if (next_e['type'] == 'expression' and
                    next_e.get('value') == 'idle' and
                    next_e['time'] - e['time'] < 0.5):
                    idle_too_early = True

        # 判断结果
        status = 'PASS' if (has_audio and emotion_match and not idle_too_early) else 'FAIL'

        # 生成详情
        details = []
        if not has_audio:
            details.append('无audio事件')
        if not emotion_match and case.expected_emotion:
            details.append(f'表情不匹配: 期望{case.expected_emotion}, 收到{emotions_received}')
        if idle_too_early:
            details.append('idle过早覆盖')

        return TestResult(
            case=case.input,
            status=status,
            detail=', '.join(details) if details else 'OK',
            events_received=len(events),
            has_audio=has_audio,
            emotion_match=emotion_match,
            idle_too_early=idle_too_early
        )

    async def run_single_round(self) -> List[TestResult]:
        """运行一轮测试"""
        round_results = []

        print(f"\n{'='*60}")
        print(f"测试轮次: {self.round_num + 1}")
        print(f"{'='*60}")

        for case in self.TEST_CASES:
            print(f"\n测试: {case.input}")
            print(f"  期望: {case.expected_emotion or '普通对话'}")

            # 重置事件记录
            self.current_events = []

            # 发送输入
            await self.send_text(case.input)

            # 等待处理完成
            await self.wait_for_completion(timeout=12)

            # 分析结果
            result = self._analyze(case, self.current_events)
            round_results.append(result)

            # 输出结果
            status_icon = '✅' if result.status == 'PASS' else '❌'
            print(f"  {status_icon} [{result.status}] {result.detail}")

            # 输出事件序列（用于调试）
            if len(self.current_events) > 0:
                print(f"  事件序列: {[e['type'] for e in self.current_events]}")

        self.round_num += 1
        return round_results

    async def run(self, rounds: int = 3):
        """
        运行多轮测试

        Args:
            rounds: 测试轮数
        """
        print(f"\n{'='*60}")
        print("表情稳定性测试")
        print(f"{'='*60}")
        print(f"测试轮数: {rounds}")
        print(f"测试用例: {len(self.TEST_CASES)}")
        print(f"服务器: {self.url}")

        try:
            await self.connect()

            for round_num in range(rounds):
                results = await self.run_single_round()
                self.results.extend(results)

            await self.disconnect()
            self._print_summary()

        except Exception as e:
            print(f"\n❌ 测试出错: {e}")
            import traceback
            traceback.print_exc()

    def _print_summary(self):
        """打印测试总结"""
        total = len(self.results)
        passed = sum(1 for r in self.results if r.status == 'PASS')

        # 按测试用例统计
        case_stats = {}
        for result in self.results:
            case = result.case
            if case not in case_stats:
                case_stats[case] = {'pass': 0, 'fail': 0}
            if result.status == 'PASS':
                case_stats[case]['pass'] += 1
            else:
                case_stats[case]['fail'] += 1

        print(f"\n{'='*60}")
        print("测试总结")
        print(f"{'='*60}")
        print(f"总计: {total} | 通过: {passed} | 失败: {total - passed} | 通过率: {passed/total*100:.1f}%")
        print(f"\n按用例统计:")
        for case, stats in case_stats.items():
            total_case = stats['pass'] + stats['fail']
            pass_rate = stats['pass'] / total_case * 100 if total_case > 0 else 0
            print(f"  {case:30s} {stats['pass']:2d}/{total_case:2d} ({pass_rate:5.1f}%)")

        # 问题分析
        idle_issues = sum(1 for r in self.results if r.idle_too_early)
        audio_issues = sum(1 for r in self.results if not r.has_audio)
        emotion_issues = sum(1 for r in self.results if not r.emotion_match)

        print(f"\n问题分析:")
        if idle_issues > 0:
            print(f"  ⚠️  idle过早覆盖: {idle_issues}/{total} ({idle_issues/total*100:.1f}%)")
        if audio_issues > 0:
            print(f"  ⚠️  audio事件缺失: {audio_issues}/{total} ({audio_issues/total*100:.1f}%)")
        if emotion_issues > 0:
            print(f"  ⚠️  表情不匹配: {emotion_issues}/{total} ({emotion_issues/total*100:.1f}%)")

        if passed == total:
            print(f"\n🎉 所有测试通过！")
        else:
            print(f"\n⚠️  部分测试失败，请查看日志分析原因")


async def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='表情稳定性测试')
    parser.add_argument('--url', default='http://localhost:12394', help='Socket.IO 服务器地址')
    parser.add_argument('--rounds', type=int, default=3, help='测试轮数')

    args = parser.parse_args()

    tester = StabilityTester(url=args.url)
    await tester.run(rounds=args.rounds)


if __name__ == '__main__':
    asyncio.run(main())
