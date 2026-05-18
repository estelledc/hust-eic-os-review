#!/usr/bin/env python3
"""为 lab5「基于内核栈切换的进程切换」11 个 step 手写 coach 与第三层 hint。"""

from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "content" / "practice-labs.json"


LAB5_HANDCRAFT: dict[str, dict] = {
    "lab5-starter-map": {
        "coach": {
            "why": "进程切换不是「改一个 pid 变量」那么简单——它要让 CPU 从「正在运行 A」变成「正在运行 B」，意味着所有寄存器、栈指针、指令指针都要被替换。这一步先确认你抓住了「现场保存 + 恢复」这个核心动作。",
            "observe": "正确选项点出「保存旧现场并恢复新现场」——这就是切换的本质。其它三个选项都把这一关搞错了：proc 文件是 Lab9、加进程编号毫无意义、启动扇区是 Lab2。",
            "act": "选出唯一同时提到「保存现场」和「恢复现场」的那一项。",
            "check": "你应该能说出：进程切换 = 保存当前 CPU 状态 + 恢复另一个进程的 CPU 状态。这两件事必须配对完成，否则进程要么停不住、要么醒不过来。",
            "repair": "如果选了 proc：那是 Lab9 的题目（虚拟文件系统）。如果选了「编号加一」：你忽略了「编号只是身份，不是状态」——CPU 不依赖编号决定下一条指令在哪。如果选了「启动扇区」：那是 Lab2，和切换无关。",
        },
        "hint3": "关键词是「现场」——这指的是 CPU 当前所有可见的执行状态（寄存器值 + 栈指针 + 指令指针）。其它选项都在改无关属性（编号 / 文件 / 启动扇区），但这些和「让 CPU 从 A 切到 B」毫无关系。找出唯一谈现场保存恢复的选项，但请用你自己的话解释为什么必须这样。",
    },
    "lab5-prepare-choice": {
        "coach": {
            "why": "「只改 current 指针」是初学者最常见的误解。current 是个内核里的全局指针，但 CPU 不读它——CPU 读的是 esp、eip 这些自己的寄存器。改 current 不会让 CPU 跳到新进程的代码，必须切换实际寄存器和栈。",
            "observe": "context 选项点出「寄存器 + 栈指针」——这才是 CPU 真正会用的状态。name-only 和 file-only 都跑题：进程名字 CPU 根本不看，日志文件和切换无关。",
            "act": "选 context：除了改 current（标记），还要把 esp、eip 等寄存器和栈指针都切到新进程的值。",
            "check": "你应该能说出：current 是「内核认为谁在跑」，CPU 寄存器是「CPU 实际在跑谁」——两者必须同时切，否则会出现「内核以为切了 B 但 CPU 还在跑 A」。",
            "repair": "如果选了 name-only：那不会让 CPU 切到任何东西。如果选了 file-only：日志和切换是两件事。回到核心：CPU 的状态在寄存器里，不切寄存器就没切。",
        },
        "hint3": "区分两个层次：内核数据结构里的「当前是谁」（current 指针）和 CPU 寄存器里的「正在跑什么」。两者的同步靠的是切换代码——它把 esp、eip、通用寄存器从 A 的备份切到 B 的备份。只改 current 的话 CPU 不会感知，但具体为什么由你自己说。",
    },
    "lab5-prepare-trace": {
        "coach": {
            "why": "切换的因果链严格固定：进程必须先进内核（被中断或主动调用 schedule）→ 保存自己的现场 → 让 schedule 选下一个 → 切换内核栈和上下文 → 恢复新进程现场。常见错排是把「保存现场」放在 schedule 之后——但 schedule 还没开始时，当前现场必须已经存好。",
            "observe": "5 个动作的状态变化：当前进程进入内核（被中断 / 主动 schedule）→ 保存当前现场（寄存器写入 task_struct 或栈）→ schedule 选下一个（看 ready 队列优先级）→ 切换内核栈和上下文（esp 切到 next 的内核栈）→ 恢复下一个进程执行（出栈到 next 的寄存器、跳到它的 eip）。",
            "act": "把「当前进程进入内核」拖到第一位、「恢复下一个进程执行」拖到最后；中间 3 步按「先保存 → 再选 → 后切」排序。",
            "check": "你应该能说出：保存必须在选择之前——否则你还没存好就被覆盖了；恢复必须在切栈之后——切栈后 esp 才指向 next 的现场备份，才能正确出栈。",
            "repair": "如果你把「保存现场」放在 schedule 之后：schedule 函数本身要用栈和寄存器，会破坏掉你想保存的现场。如果把「切换内核栈」放在「保存现场」之前：保存写到哪里？写到 next 的栈？那就乱了。",
        },
        "hint3": "对每两个相邻动作问「上一步是不是为下一步准备了状态」。schedule 选下一个之前，当前进程的现场必须已存好（否则被 schedule 覆盖）；切换内核栈之后才能恢复——esp 切到 next 的栈才能出栈到 next 的寄存器。中间 3 步按这条因果排，但请你自己确认。",
    },
    "lab5-observe-diagnose": {
        "coach": {
            "why": "「切换后从奇怪位置继续」是 Lab5 最经典的现象。原因几乎总是同一类：现场保存或恢复时漏了某个寄存器（比如忘了保存 ebp，恢复后栈帧错位）、或栈指针切换时机不对（切早了把 next 的现场写到了自己的栈）。",
            "observe": "stack-frame 选项点出「栈或现场保存/恢复不完整」——这是切换错乱的真因。tty-buffer 和 image-old 都是无关因素：终端输入和切换没关系，显卡字体不影响 CPU 跳转。",
            "act": "选 stack-frame：去检查 switch_to 汇编里 push/pop 的寄存器列表是否对齐、esp 切换的时机是否正确。",
            "check": "你应该能说出：切换异常的根因永远在「现场保存/恢复」这条路径上——不会是无关的显卡或终端问题。",
            "repair": "如果选了 tty-buffer 或 image-old：那是和切换正交的子系统。回到 Lab5：现场 = 寄存器列表 + 栈指针 + 指令指针，三者中任何一个不对都会让 CPU「从奇怪位置继续」——因为 CPU 严格按 eip 取指，eip 错了就跳错位置。",
        },
        "hint3": "切换异常的诊断三步走：① 看 switch_to 汇编里 push/pop 是不是对称（push 5 个 pop 必须 5 个）；② 看 esp 切换是不是发生在保存之后；③ 看 task_struct 里保存现场的字段有没有被别处篡改。具体顺序由你判断。",
    },
    "lab5-observe-fill": {
        "coach": {
            "why": "内核栈和 schedule 是 Lab5 的两个核心名字——一个是「现场存放的物理位置」，一个是「决定谁是下一个的函数」。两者必须叫准，否则讨论切换时全在含糊其辞。",
            "observe": "观察两个空的状态：第一空指向「进程在内核里跑代码时用的栈」（这是内核栈，每进程独立、不和用户栈共享）；第二空指向「内核里负责挑下一个 ready 进程的函数」（这是 schedule()）。两者一个是数据结构、一个是函数。",
            "act": "stack 空填「内核栈」（也接受 kernel stack），scheduler 空填 schedule。",
            "check": "你应该能说出：内核栈是「位置」（一段内存）、schedule 是「动作」（一个 C 函数）——两者各管一头。Lab5 的关键是 schedule 函数会改写 esp 切到目标进程的内核栈。",
            "repair": "如果第一空填了「用户栈」：那是 Lab5 不研究的——切换发生时进程已经从用户态进了内核，用户栈早被冻结。如果第二空填了 fork 或 exit：那是别的进程动作，不是「选谁跑」的函数。",
        },
        "hint3": "区分两个名字：内核栈（数据，进程在内核态时用的栈）vs schedule（函数，从 ready 队列挑下一个）。第一空找「位置」「栈」类的术语，第二空找「函数名」。提示语 placeholder 已经有线索，但请你确认为什么。",
    },
    "lab5-operate-command": {
        "coach": {
            "why": "Lab5 修改的是内核里 kernel/sched.c 等文件，所以 cd 进 kernel 子目录后局部 make 就够了——不像 Lab1 是整体 make。这一步在让你区分「整体 make」和「针对子系统 make」。",
            "observe": "starter 第一条 cd oslab/linux-0.11/kernel 把你站到内核 C 文件目录。下一条 make 只编译这一片（包括 sched.c、fork.c、signal.c）。再 cd ../../ 退两层到 oslab，最后 ./run switch-trace 启动并加载切换观察脚本。",
            "act": "在第一条之后追加 make → cd ../../ → ./run switch-trace。注意 cd ../../ 是退两层（kernel → linux-0.11 → oslab）。",
            "check": "你应该能说出：cd 进 kernel 而不是 linux-0.11，意味着你只编内核子系统而不重编整个内核——速度快但要求你确实改的是 kernel/ 下的文件。",
            "repair": "如果 cd 只到 linux-0.11：你做的是整体 make，浪费时间。如果 cd .. 只退一层：./run 找不到（它在 oslab 根）。如果 ./run 没带 switch-trace：Bochs 启动了但没加载切换专用观察脚本。",
        },
        "hint3": "Lab5 的命令链有两个细节：cd 进了 kernel 子目录（不是 linux-0.11 顶层），所以 cd 退要退两层（cd ../../）；./run 后接 switch-trace 参数指定加载切换观察。具体写法你自己来。",
    },
    "lab5-operate-code": {
        "coach": {
            "why": "切换代码的三个核心要素：被切换的对象（task_struct）、切换动作本身（switch）、被保存的关键数据（stack 现场）。这一步让你用三个关键词锚定切换代码必涉及的三件事——任何缺一就不是完整切换。",
            "observe": "starter 给了 task_struct *next 和两行注释提示。task_struct 是被切换对象的描述（含 esp 字段保存内核栈位置）、switch 是动作、stack 是关键数据（current 进程的栈现场要存进 task_struct，next 进程的栈要被恢复）。",
            "act": "保留 starter 的结构，确保 task_struct、switch、stack 三个词在你的片段里都出现，可以加一行注释（比如「switch_to(current, next): save current's stack ptr to current->kernel_stack, load next's」）。",
            "check": "你应该能说出：切换的最小语义就是「把 current 的 esp 存到 current->task_struct，把 next 的 esp 从 next->task_struct 取出来」——三个关键词的角色互不替代。",
            "repair": "如果你只用了 task_struct 和 switch 没用 stack：那等于说「我切换了一个对象」但没说切的是什么——切换的本质就是栈/寄存器现场。三个词缺一就缺一个层面。",
        },
        "hint3": "switch_to 函数的最小描述：从 task_struct 取 next 的栈指针、把当前栈指针存到 task_struct——三个关键词都自然涉及。不必写完整汇编，只要片段能体现这三件事的关系，但请用一句话连起来。",
    },
    "lab5-operate-explain": {
        "coach": {
            "why": "「为什么 schedule 之后还要切上下文」是初学者经常困惑的——schedule 不是已经选好了吗？答案是：schedule 只是「决策」（选谁），上下文切换才是「执行」（让 CPU 真切到那个进程）。决策不等于执行，必须配套。",
            "observe": "三个关键词的因果：调度（决策：选下一个）→ 现场（决策完成后要保存当前 + 恢复目标）→ 内核栈（现场就保存在内核栈附近，esp 切到 next 的内核栈才能完成恢复）。三件事必须连续完成。",
            "act": "写 2-3 句话，按「schedule 只是选 → 选完还要切 → 切的核心是内核栈现场」的顺序，三个词全用上。",
            "check": "你应该能说出：调度是「计划」，切换是「执行」——只有计划没有执行，CPU 还在跑老进程。",
            "repair": "如果只写了三个词没说因果：那是堆砌。补一句「schedule 决定下一个是 next，但 CPU 不知道；要把 esp、eip、寄存器从 current 切到 next，CPU 才会跑 next」。",
        },
        "hint3": "三个词的层次：调度（高层决策）→ 内核栈（中层载体）→ 现场（底层数据）。schedule 选完之后，必须沿着这条层次往下走完，才算切换完成。具体怎么写让用户跟着想清楚由你来。",
    },
    "lab5-full-depth-1": {
        "coach": {
            "why": "「不保存会怎样」是理解切换的反面问题——只有想清楚「丢了哪一类信息会出什么错」，你才真正理解每个保存动作的必要性。这一步用反向问题逼你检查每个寄存器/栈帧的角色。",
            "observe": "三个关键词在 Lab5 的角色：现场（被保存的对象）、内核栈（保存的位置）、恢复（保存的对偶动作）。如果不保存：通用寄存器丢了 → 计算结果错；esp/ebp 丢了 → 栈帧解读错；eip 丢了 → 跳到任意地址；段寄存器丢了 → 内存访问错。",
            "act": "写 3 句话以上：① 不保存通用寄存器会怎样（计算结果错）；② 不保存 esp/eip 会怎样（栈帧错位 + 跳错地址）；③ 内核栈本身的角色（既是保存位置，也是 esp 切换目标）。",
            "check": "你应该能说出：每一类寄存器丢失都对应一种可观察的错误现象——这就是为什么切换代码要 push 整套寄存器。",
            "repair": "如果你写得很泛（「会出错」「程序崩溃」）：那是没说清。补上具体——「丢了 eax 计算结果错，丢了 esp 出栈位置错，丢了 eip CPU 直接跳到随机地址」。",
        },
        "hint3": "把寄存器分类讨论：通用寄存器（eax-edx）丢了影响计算结果，栈寄存器（esp/ebp）丢了影响栈帧，控制寄存器（eip/eflags）丢了影响下一步执行。逐类说明丢失会出什么具体错——但具体写法你自己来。",
    },
    "lab5-full-depth-2": {
        "coach": {
            "why": "Lab5 关注内核栈而不是用户栈，是因为切换发生在「进程已经进了内核」的时候——schedule 是内核函数，调用它意味着进程已经从用户态切到内核态、esp 已经从用户栈切到内核栈。所以保存的是当下 CPU 用的栈，也就是内核栈。",
            "observe": "三个关键词的关系：用户栈（用户态时用）vs 内核栈（内核态时用）vs 切换（发生的位置）。切换不会发生在用户态——用户态执行普通指令时不会主动 schedule，所以切换发生时已经在内核态了。",
            "act": "写 3 句话以上：① 切换发生在哪（内核态 schedule 调用时）；② 那一刻 CPU 用的栈是什么（内核栈）；③ 用户栈是什么状态（已被冻结、不参与切换）。",
            "check": "你应该能说出：「切换关注内核栈不关注用户栈」不是设计选择，是事实——切换那一刻用户栈根本没在用。",
            "repair": "如果你说「内核栈更重要」：那是结论不是解释——补上「切换发生时进程已经在内核里跑，所以当前活跃的栈就是内核栈，用户栈这时已经冻结」。",
        },
        "hint3": "切换的位置很关键：它发生在 schedule 函数里，schedule 是内核函数，所以调用它时进程已经是内核态、当前 esp 指向内核栈。用户栈这时已被搁置——和切换无关。三个关键词必须连同「位置」一起说，但具体写法你自己给。",
    },
    "lab5-reflect-summary": {
        "coach": {
            "why": "复盘要把「切换 = 现场保存 + 恢复 + 内核栈是关键载体」沉淀下来。三句话的用途：第一句答驱动问题（说出内核栈为什么决定停/续位置）、第二句标记最易混的边界（用户栈 vs 内核栈、决策 vs 执行）、第三句给真实实验留具体证据。",
            "observe": "驱动问题：「进程切换时，为什么内核栈会影响『从哪里停下、从哪里继续』？」第一句回答：因为停下来的位置（eip/esp）保存在内核栈附近的 task_struct 字段里，恢复时 esp 切回那个内核栈才能取出现场。",
            "act": "三段：① 内核栈在切换中的角色（保存现场的载体 + esp 切换目标）；② 最易混的边界（用户栈 vs 内核栈、schedule 决策 vs switch_to 执行）；③ 真实实验时第一个看的证据（switch_to 的 push/pop 列表、task_struct 的 esp 字段、内核栈布局）。",
            "check": "你应该能说出：以后遇到「切换异常」就能直接定位到「内核栈是不是切对了」「现场是不是存全了」——而不是乱猜。",
            "repair": "如果三句话很泛：把每句换成具体动作（grep switch_to 看 push/pop / 看 task_struct 字段 / 加 trace 打 esp 值）。",
        },
        "hint3": "压成 3 句：第一句答「内核栈如何承载停/续位置」；第二句指出最易混的边界（用户栈 vs 内核栈、决策 vs 执行）；第三句留真实实验时第一个要看的证据（switch_to 汇编 / task_struct.esp）。具体内容你自己来。",
    },
}


def main() -> None:
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    lab = next(lab for lab in data["labs"] if lab["id"] == "lab5")
    written = 0
    total = sum(len(p["steps"]) for p in lab["phases"])
    for phase in lab["phases"]:
        for step in phase["steps"]:
            craft = LAB5_HANDCRAFT.get(step["id"])
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
    print(f"已为 lab5 手写 {written}/{total} 步")


if __name__ == "__main__":
    main()
