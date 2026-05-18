#!/usr/bin/env python3
"""为 lab4「进程运行轨迹的跟踪与统计」10 个 step 手写 coach 与第三层 hint。"""

from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "content" / "practice-labs.json"


LAB4_HANDCRAFT: dict[str, dict] = {
    "lab4-starter-map": {
        "coach": {
            "why": "进程是看不见的——它们在 CPU 里被调度切换，但你既看不到 ready 队列里有谁、也看不到为什么某个进程被换下去。Lab4 的核心动作是「让看不见的状态变化留下文字痕迹」。这一步先确认你抓住了「记录」这个目的。",
            "observe": "正确选项点出「把状态变化记录成日志」——这就是 Lab4 的本质。其它选项指向了别的实验：proc 是 Lab9、终端回显是 Lab8、改进程名字根本没意义。",
            "act": "选出唯一同时提到「进程状态」和「记录」的那一项。",
            "check": "你应该能说出：调度的状态变化（ready ↔ running ↔ blocked）发生在内核里、用户看不到——必须用日志把它「印」出来才能分析。",
            "repair": "如果选了 proc 虚拟文件：那是 Lab9 的题目（虚拟文件如何动态生成）。如果选了终端回显：那是 Lab8。如果选了改名字：那对调度行为本身没影响——名字不是状态。",
        },
        "hint3": "「轨迹」这个词是关键——它隐含「时间序列 + 状态变化」。其它选项要么换主题（proc/终端）、要么把无关属性（名字）当成研究对象。找出唯一同时提及「状态变化」和「记录/日志」的那一句，但请用你自己的话说为什么必须记录。",
    },
    "lab4-prepare-choice": {
        "coach": {
            "why": "日志不是越多越好，而是「能不能还原过程」。state-time 选项给出了能还原过程的最小字段集：pid（谁）、时间（何时）、状态变化（发生了什么）、原因（为什么）。少了任何一项，日志就还原不出完整的调度故事。",
            "observe": "only-name 缺时间——你看不出事件发生顺序；only-color 完全无关——颜色不是进程状态。state-time 列的四个字段对应「四 W」：who（pid）、when（time）、what（state change）、why（cause）。",
            "act": "选 state-time：只有这套字段能让日志「可分析」——你能从中算等待时间、推断调度策略、找出阻塞原因。",
            "check": "你应该能说出：日志的字段集决定了你能从日志里提取哪些结论——字段不够，再多行也分析不出有用结果。",
            "repair": "如果选了 only-name：你会发现日志里全是「进程 A 在做事」但说不清「在哪个时刻、做什么改变」。如果选了 only-color：那是装饰，不是分析素材——颜色变化不对应任何调度事件。",
        },
        "hint3": "想象你拿到一份日志，要算「进程 A 等了多久」——你需要至少两个时间点（开始等、被唤醒）和确认「A」的方式（pid）。少 pid 你不知道哪条属于谁，少时间你不知道间隔多长，少状态变化你不知道事件是什么——四个字段一个不能少，但请你自己解释为什么。",
    },
    "lab4-prepare-trace": {
        "coach": {
            "why": "进程的生命周期有固定阶段：被创建 → 进就绪队列 → 被调度运行 → 因某种原因离开 CPU → 后续被记录。常见错排是把「日志统计」混进中间——其实日志是观察手段，本身不在因果链里，只在最后总结时出现。",
            "observe": "5 个动作的状态变化：创建进程（task_struct 被分配）→ 进入就绪队列（state=TASK_RUNNING 但没拿到 CPU）→ 被调度运行（schedule 选中，CPU 切到它）→ 因等待或时间片切换（state 变 TASK_INTERRUPTIBLE 或被换下）→ 日志统计状态轨迹（事后处理）。",
            "act": "把「创建进程」拖到第一位、「日志统计状态轨迹」拖到最后；中间 3 步按「进队列 → 拿 CPU → 离 CPU」排序。",
            "check": "你应该能说出：进程不会跳过任何一步——必须先创建才能就绪、先就绪才能运行、先运行才能因等待/切片离开。日志只是把这条因果序列「印下来」。",
            "repair": "如果你把「日志统计」放在中间：你混淆了「观察手段」和「被观察对象」——日志在所有动作完成后才汇总分析，不是动作之一。如果把「就绪」和「运行」颠倒：那 CPU 怎么知道选谁运行？得先有 ready 队列才能挑选。",
        },
        "hint3": "进程的状态从来不会从「被创建」直接到「运行」——必须先进 ready 队列，因为调度器只从 ready 队列里挑。日志是事后的归纳，不在因果链中间。把 5 个动作分成「进程经历」和「事后观察」两类，顺序就出来了——但请你自己说清因果。",
    },
    "lab4-observe-diagnose": {
        "coach": {
            "why": "日志缺状态变化几乎总是同一类原因：你的 trace 调用没埋在所有「状态变量被赋新值」的地方。比如你只在 schedule() 里 trace 了 running 切换，但忘了 wake_up() 里的 blocked → ready，结果就一段空白。",
            "observe": "trace_points 直接指向问题根源：观察点（trace 调用）的覆盖范围决定了日志能看到什么。wrong-font 和 wrong-proc 都是无关因素——前者只影响显示美观，后者属于 Lab9。",
            "act": "选 trace_points：去 grep 内核里所有 state 变量被赋值的位置，确认 trace 调用都到位了。",
            "check": "你应该能说出：日志里看不见的事件 = 没埋 trace 的事件——不是「事件没发生」，是「发生了但没被记录」。",
            "repair": "如果选了 wrong-font：日志的可读性问题不会让事件消失，只会让你读不舒服。如果选了 wrong-proc：proc 是 Lab9，和这里的「内核函数里埋点」无关。回到 Lab4：每一处 state = TASK_XXX 的赋值都该有 trace。",
        },
        "hint3": "日志缺事件的诊断方法是「反向归因」：先列出你期望看到的所有状态变化，再 grep 内核源码看哪些位置赋值了 state 变量，对照看哪些位置缺 trace 调用。覆盖率不够就一定有空白——但具体怎么 grep 由你来。",
    },
    "lab4-observe-fill": {
        "coach": {
            "why": "ready 和 blocked 是进程状态的两个核心名字——一个是「能跑但没轮到」，一个是「不能跑因为在等」。Lab4 的日志最常记录的就是这两种状态之间的切换，所以名字必须叫准。",
            "observe": "观察两个空对应的进程状态：第一空指向「state == TASK_RUNNING 但当前不在 CPU 上」（这就是 ready），第二空指向「state == TASK_INTERRUPTIBLE/UNINTERRUPTIBLE」（这就是 blocked / sleep）。",
            "act": "ready 空填「就绪」（也接受 ready），blocked 空填「阻塞」（也接受 blocked / sleep）。",
            "check": "你应该能说出：ready 不等于 running——前者在排队，后者在 CPU 上。blocked 不等于死亡——前者在等条件成立，醒来还能 run。",
            "repair": "如果第一空填了「运行」：你混淆了 ready 和 running——running 是「正在 CPU 上的那个」，ready 是「还没轮到的那些」。如果第二空填了「停止」：那是另一种状态（被信号 STOP 暂停），不是因等待事件而暂停。",
        },
        "hint3": "ready 队列里有多个进程——它们都「想跑」，调度器从中挑一个真正运行。blocked 的进程不在 ready 队列，要等条件触发才被唤回 ready。第一空是「想跑但没轮到」，第二空是「不想跑（在等什么）」——但答案要用术语本身。",
    },
    "lab4-operate-command": {
        "coach": {
            "why": "Lab4 不仅要构建内核，还要跑一个观察程序看日志输出——所以 ./run 后接 process-log 这个观察脚本。这一步在让你区分「构建」和「跑观察程序」是两个独立步骤。",
            "observe": "starter 第一条 cd oslab/linux-0.11 切到源码目录。下一条 make 编进新的 trace 调用。再 cd .. 退到 oslab，最后 ./run process-log 启动 Bochs 并指定加载观察日志的脚本——日志是这一步产生的现象。",
            "act": "在第一条之后追加 make → cd .. → ./run process-log。",
            "check": "你应该能说出：构建产生「带 trace 埋点的内核」，./run process-log 产生「实际运行时的日志」——前者是工具，后者是数据。两者都要做才有可分析素材。",
            "repair": "如果用了 ./run 而不是 ./run process-log：Bochs 启动了，但你看不到专门收集进程轨迹的输出——只是普通启动而已。Lab4 的日志现象需要观察脚本配合才会出现。",
        },
        "hint3": "Lab4 的 ./run 后面要跟 process-log 这个参数，提示 Bochs 启动后跑收集进程日志的程序——这是 Lab4 比 Lab1 多出来的细节。前三条命令和 Lab1 一致，第四条要带参数——但具体写法你自己来。",
    },
    "lab4-operate-code": {
        "coach": {
            "why": "trace_state 是 Lab4 的典型埋点函数——它必须接收 pid（谁的状态变了）和 state（变成什么），并加上时间戳生成日志条目。三个关键词缺任何一个日志都不可分析。",
            "observe": "starter 给了函数签名 trace_state(int pid, int state) 和注释提示。pid 已经在参数里、state 也在参数里——你要做的是让函数体里出现 trace 这个动作（写日志），三个关键词同时出现。",
            "act": "在函数体里写出实际 trace 动作（比如调一个 trace_log(pid, state, jiffies) 或保留注释意图），保证 pid、state、trace 三个词都在片段里。",
            "check": "你应该能说出：每条日志至少包含 pid + state + 时间——少 pid 不知道是谁、少 state 不知道事件、少时间不知道顺序。",
            "repair": "如果只写了 pid 和 state 没写 trace：那是函数签名没函数体——参数被传进来但没人记录它们。补上一行实际写日志的动作。",
        },
        "hint3": "trace_state 函数的工作就是把入参（pid + state）连同时间戳记到日志缓冲区。三个关键词：pid（被记录的对象）、state（被记录的事件）、trace（记录这个动作本身）。最简的实现就一行——但你自己写，不要直接抄。",
    },
    "lab4-operate-explain": {
        "coach": {
            "why": "「一行日志说明不了调度」——因为调度本质是状态切换，至少需要两个时间点（切换前/后）才能体现「变化」。这一步在让你从「就绪、运行、阻塞」三个状态出发，说明为什么必须记录跨状态的轨迹。",
            "observe": "三个状态是闭环：就绪 → 运行 → 阻塞 → 就绪 → ... 只看一行日志只能看到瞬时快照，看不到状态之间的迁移——而调度行为完全体现在迁移里（什么时候被换下、为什么被换、等多久）。",
            "act": "写 2-3 句话，按「单行只是快照 → 调度发生在迁移 → 必须看连续多行才能看到迁移」的顺序，三个状态词都用上。",
            "check": "你应该能说出：日志的「连续两行」是分析单位，不是「一行」——比较两行才能算出等待时间、判断调度策略、推断阻塞原因。",
            "repair": "如果只写了三个状态名没说「为什么连续多行才有用」：你只列了概念没解释为什么需要轨迹。补一句「相邻两行的状态变化告诉你一次调度事件」。",
        },
        "hint3": "调度的本质是「让 CPU 在 ready 进程间切换」——这种切换发生在「running → ready」「running → blocked」「blocked → ready」等迁移上。每次迁移在日志里至少占两行（前一状态 + 后一状态）。三个状态词必须连同迁移一起说，但具体写法你自己来。",
    },
    "lab4-full-depth-1": {
        "coach": {
            "why": "日志只是文本，单看文本不够——你必须知道「这行日志对应的 trace 调用埋在哪个函数里」才能解读它。这一步要求你说出「日志、状态、调度」三者的关系：调度发生 → 在埋点处记录 → 产生日志。",
            "observe": "三个关键词的因果：调度（行为）→ 状态（被改变的内核数据）→ 日志（被记录的事实）。如果你只看日志不知道埋点位置，遇到「state=2」这种数字根本不知道是什么状态变化。",
            "act": "写 3 句话以上：① 日志为什么不能脱离记录点解读（数字/缩写需要上下文）；② 状态和调度的关系（调度改变状态）；③ 完整解读流程（事件 → 状态变化 → 埋点记录 → 日志条目）。",
            "check": "你应该能说出：分析日志必须配合 trace 调用的源码位置——单看日志文本只是「字符」，需要知道每条来自哪个埋点才能映射回真实事件。",
            "repair": "如果你只罗列三个词：那是没说清因果。补上「调度做什么、状态在哪里、日志怎么联系两者」——三件事的关系不是平行的，是有层次的。",
        },
        "hint3": "日志、状态、调度三者：调度是动作（schedule 选谁跑、何时切换），状态是数据（task_struct.state 字段），日志是产物（trace 调用把状态变化记下来）。三者的因果关系是「调度产生状态变化、状态变化由日志记录」——但具体怎么写得清楚由你来。",
    },
    "lab4-reflect-summary": {
        "coach": {
            "why": "复盘要把「让看不见的进程留下文字痕迹」这个核心方法论沉淀下来。三句话用途：第一句答驱动问题（说出「埋点 + 字段集」）、第二句标记最易混的边界（事件 vs 状态、状态 vs 名字）、第三句给真实实验留具体证据（看哪些函数里有 trace、看日志有哪些必备字段）。",
            "observe": "驱动问题：「进程运行看不见时，怎样记录轨迹并从轨迹里看懂调度？」第一句直接回答：在所有 state 赋值处埋 trace 调用，记 pid + state + 时间 + 原因。",
            "act": "三段：① 完整记录方法（埋点 + 字段集）；② 最易混的边界（ready vs running、状态 vs 调度行为、日志 vs 解读）；③ 真实实验时第一个看的证据（grep state 赋值看埋点覆盖率、日志样本看字段是否齐全）。",
            "check": "你应该能说出：以后看任何 OS 日志都能立刻问「字段够吗？埋点全吗？」——这是 Lab4 训练的核心能力。",
            "repair": "如果三句话很泛：把每句换成具体动作。比如「我会先 grep 'state =' 找所有状态赋值点」「我会确认日志格式包含 pid 和时间戳」。",
        },
        "hint3": "压成 3 句：第一句给出 Lab4 的方法论（在 state 赋值处埋点、记最小可分析字段集）；第二句指出最易混的边界（状态 vs 名字、事件 vs 行为）；第三句留一个真实实验的具体动作（grep 埋点 / 检查字段完整性）。具体内容你自己写。",
    },
}


def main() -> None:
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    lab = next(lab for lab in data["labs"] if lab["id"] == "lab4")
    written = 0
    total = sum(len(p["steps"]) for p in lab["phases"])
    for phase in lab["phases"]:
        for step in phase["steps"]:
            craft = LAB4_HANDCRAFT.get(step["id"])
            if not craft:
                print(f"  [skip] {step['id']} 未提供手写内容")
                continue
            step["coach"] = craft["coach"]
            for hint in step.get("hints", []):
                if hint.get("level") == 3:
                    hint["text"] = craft["hint3"]
            written += 1
    DATA_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"已为 lab4 手写 {written}/{total} 步")


if __name__ == "__main__":
    main()
