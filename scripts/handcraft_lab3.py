#!/usr/bin/env python3
"""为 lab3「系统调用」10 个 step 手写 coach 与第三层 hint。"""

from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "content" / "practice-labs.json"


LAB3_HANDCRAFT: dict[str, dict] = {
    "lab3-starter-map": {
        "coach": {
            "why": "系统调用不是「换个名字的函数」。它是用户态唯一安全进入内核的方式——为什么需要这个机制，是 OS 设计的核心问题。这一步在确认你抓住了「受控入口」这个关键概念。",
            "observe": "正确选项点出「受控入口请求内核服务」——这是系统调用的本质。其它三个错的方向：终端颜色（无关）、改函数名（忽略了特权级）、地址映射（混到了 Lab7 的内容）。",
            "act": "选出唯一同时提到「用户程序」和「请求内核服务」的那一项。",
            "check": "你应该能说出：用户程序和内核处在不同的特权级，普通函数调用不能跨级——必须有一种受控的、可被内核审查的方式发起请求。",
            "repair": "如果选了「改终端颜色」：那是用户态完全可做的事，不需要系统调用。如果选了「换函数名」：你忽略了「为什么内核函数不能直接被用户调用」。如果选了「地址映射」：那是 Lab7 的主题，不是 Lab3。",
        },
        "hint3": "「系统调用」和「函数调用」最大区别在「跨边界」——不是技术细节问题，而是安全模型问题。用户态的代码不被信任，内核必须自己决定「我接受哪些请求」。在选项里找强调这种「受控」性质的那一句，但请用你自己的话说为什么需要受控。",
    },
    "lab3-prepare-choice": {
        "coach": {
            "why": "把系统调用看成「特殊的函数调用」是最常见的初学者错误。privilege-boundary 选项强调的「特权级跨越」才是它和函数调用的本质区别——必须经过 CPU 的特权级切换机制（int 0x80 触发），而不是简单的 jmp 或 call。",
            "observe": "same-stack 错把系统调用当成同栈跳转——但实际上用户态有用户栈、内核态有内核栈，跨入口时栈也要切。no-return 是另一种误解——系统调用最终是要返回的，否则用户程序就永远停在了内核里。",
            "act": "选 privilege-boundary：这是唯一抓住「跨特权级、必须经受控入口」的选项。",
            "check": "你应该能说出：系统调用 = 特权级跨越 + 受控入口 + 受控返回。这三件事普通 C 函数调用一件都不需要，所以本质不同。",
            "repair": "如果选了 same-stack：你忽略了 CPU 在特权级切换时会自动切栈（从 ss:esp 切到 tss 中保存的内核栈）。如果选了 no-return：你忘了 sys_xxx 末尾的 iret 指令会让 CPU 切回用户态继续执行下一条用户指令。",
        },
        "hint3": "用户态和内核态在 CPU 里是不同的特权级（DPL 0 vs 3）——CPU 的硬件机制就阻止了用户态代码直接跳到内核地址执行。系统调用必须借助一种 CPU 认可的「合法跨级」方式（中断/陷阱），所以它和普通 call 在硬件层就不同。具体怎么不同请你自己解释。",
    },
    "lab3-prepare-trace": {
        "coach": {
            "why": "5 个动作的顺序固定：用户调封装 → int 0x80 触发 → system_call 收下 → 查 sys_call_table → 执行 sys_xxx → 返回。每一步都依赖前一步留下的状态：寄存器里的系统调用号、栈上的参数、CPU 的特权级。",
            "observe": "状态变化：用户程序调用封装（系统调用号写入 eax）→ int 0x80 触发（CPU 切到内核态、切到内核栈）→ 进入 system_call（汇编入口，保存现场）→ 用 eax 索引 sys_call_table（拿到 sys_xxx 地址）→ 调 sys_xxx → 返回（iret）。",
            "act": "把「用户程序调用封装」拖到第一位、「执行 sys_xxx 并返回」拖到最后；中间 3 步按「触发 → 入口 → 查表」排序。",
            "check": "你应该能说出：每一步都为下一步准备了某种状态——eax 里的调用号、内核栈上的现场、sys_call_table 给出的目标地址。这条链断在哪里都会失败。",
            "repair": "如果你把「索引 sys_call_table」放在 system_call 之前：system_call 还没执行，谁去做这个查表？如果把「int 0x80」放在「调用封装」之前：用户调用封装本身就包含了 int 0x80 这条指令，顺序不能颠倒。",
        },
        "hint3": "整条链有两次「换手」：用户态 → 内核态发生在 int 0x80（硬件协助），内核入口 → 具体处理函数发生在 sys_call_table（软件查表）。识别这两个换手点，剩下的 3 个动作就只能各自落到固定位置——但请你自己确认顺序。",
    },
    "lab3-observe-diagnose": {
        "coach": {
            "why": "「能编译但结果不对」在系统调用里几乎总是同一类原因：用户的系统调用号和 sys_call_table 的索引对不上——比如号是 72 但表里 72 号位置是别的函数（或干脆没填）。这是 Lab3 必须诊断的第一类错误。",
            "observe": "三个选项里只有 table-number 把你引向真正可以观察的证据：去看 sys_call_table 在内核里的内容、去看用户头文件里的 #define 编号——两边的状态对上了才说明链路通。screen-theme 和 boot-sector-size 都不会留下任何系统调用相关的现象，看了也没用。",
            "act": "选 table-number：先 grep 系统调用号在用户头文件里的定义，再核对内核 sys_call_table 同一索引上的函数指针。",
            "check": "你应该能说出：系统调用号是用户和内核之间的「契约编号」——双方对同一个号的理解必须一致，否则用户喊 72 号、内核接到了别的事，结果当然不对。",
            "repair": "如果选了 screen-theme 或 boot-sector-size：那是不会影响系统调用语义的因素。回到 Lab3 的链路：用户的 #define __NR_xxx 必须和内核 sys_call_table 的同号位置完全对应——这是 Lab3 加新系统调用时最常忘的一步。",
        },
        "hint3": "加新系统调用时，你需要在三处同步：用户头文件里的 #define __NR_xxx、内核的 sys_call_table[xxx] 函数指针、sys_xxx 函数本身。漏改任意一处都会让用户和内核「号对不上」。具体先查哪一处由你判断。",
    },
    "lab3-observe-fill": {
        "coach": {
            "why": "int 0x80 和 sys_call_table 是 Lab3 的两个核心名字。一个是「跨级入口」（硬件机制：触发 0x80 号软中断让 CPU 切到内核态），一个是「查表机制」（软件机制：用调用号索引函数指针表）。两者各管一半。",
            "observe": "观察两个空对应的状态——第一空是 CPU 切换状态时的入口（实模式下用户态运行 int 0x80 这条指令时的硬件现象就是切到内核态、跳到 IDT[0x80] 指向的代码），第二空是内核数据结构的状态（一张静态数组，每项是函数指针）。两者一个是动作、一个是数据。",
            "act": "entry 空填 int 0x80（也接受 0x80），table 空填 sys_call_table。",
            "check": "你应该能说出：int 0x80 是「怎么进入内核」的答案，sys_call_table 是「进入后做什么」的答案——两个名字解决两个不同的问题。",
            "repair": "如果第一空填了 system_call：那是 int 0x80 触发后 CPU 跳到的代码地址，不是「入口」本身——入口是中断号 0x80，不是中断处理代码。",
        },
        "hint3": "区分「机制」和「代码」：int 0x80 是机制（CPU 的中断号），system_call 是代码（处理这个中断的汇编入口）。第一空要填的是机制本身的名字。第二空是表的名字——内核里有一张被索引访问的指针表，名字直接叫它。",
    },
    "lab3-operate-command": {
        "coach": {
            "why": "和 Lab1 一样的四条命令——但这次目的不同：你要观察的不是 Image 是否更新，而是新加的系统调用能不能被用户程序调到。所以构建后要在 Bochs 里跑用户程序看返回值。",
            "observe": "starter 第一条 cd oslab/linux-0.11 把你切到源码顶层。下一条 make 重新编译内核（包括 sys_call_table 的修改）。再 cd .. 回到 oslab，./run 启动 Bochs——启动后用户程序需要在虚拟磁盘里手动跑。",
            "act": "在第一条之后追加 make → cd .. → ./run。",
            "check": "你应该能说出：构建只是第一步，Lab3 的真正验证是在 Bochs 里跑用户测试程序看 syscall 返回——构建产生新内核，运行用户程序产生证据。",
            "repair": "如果你 make 漏了：./run 启动的还是老内核，你的 sys_call_table 修改根本没进去——用户程序看到的还是旧行为，让人误以为「修改没生效」。",
        },
        "hint3": "命令链和 Lab1 一样，但你要明确每条命令在 Lab3 上下文里的意义：make 编进 sys_call_table 的修改、./run 启动后才有用户程序运行环境去测 syscall。具体写法你自己来。",
    },
    "lab3-operate-code": {
        "coach": {
            "why": "添加 sys_demo 不止是写函数体——还要把它「挂到」sys_call_table 上，否则用户即使调用对应的号也找不到这个函数。三个关键词分别对应：函数本身（sys_demo）、它的返回值（return）、把它暴露出去的入口（sys_call_table）。",
            "observe": "starter 已经写了 sys_demo 的最小函数体（return 0）和一行注释提示「add sys_demo to sys_call_table」。你要做的是让代码片段同时体现这三件事——函数定义、返回动作、表注册。",
            "act": "保留 sys_demo 函数定义和 return 0；在注释处补一行表示要把它注册到 sys_call_table（比如「sys_call_table[__NR_demo] = sys_demo;」或保留注释意图）。三个关键词都要出现。",
            "check": "你应该能说出：函数 + 注册是两件事，缺哪件都不行——只写函数没注册，用户调不到；只注册没函数，链接器报错。",
            "repair": "如果你只写了 sys_demo 没写 sys_call_table：那是写了一半——内核里多了一个孤立函数，用户程序根本不知道怎么调它。补上注册的一行（哪怕只是注释意图）。",
        },
        "hint3": "Lab3 加新系统调用必须改三处：用户头文件 #define、sys_call_table 入口、sys_xxx 函数。这一步只问你后两件事——把 sys_demo 函数和 sys_call_table 都写进片段就行，但请用一句话说清它们的关系。",
    },
    "lab3-operate-explain": {
        "coach": {
            "why": "「为什么不能直跳到 sys_demo」是 Lab3 最值得理解的问题。答案不是「内核地址你不知道」（其实可以知道），而是「CPU 拒绝你这么干」——用户态的 jmp 一旦跳到内核地址，CPU 会直接抛出 GPF（一般保护异常）。这是硬件层的安全门。",
            "observe": "三个关键词的因果：用户态（DPL=3）和内核态（DPL=0）是 CPU 的两种特权级；普通跳转必须 DPL <= 目标段 DPL，所以用户态的 jmp 进不了内核段。系统调用号是穿过这道门的「编号通行证」——CPU 只放编号通行证的请求过去。",
            "act": "写 2-3 句话，按「为什么不能直跳 → 系统调用号是合法通道 → 走这个通道就安全可控」的顺序，三个关键词全用上。",
            "check": "你应该能说出：CPU 的特权级机制是硬件级的——不是「我们设计成不让跳」，而是「就算你写 jmp 0xC0000000，CPU 也会立刻把你的进程杀掉」。这是设计的根。",
            "repair": "如果你只写了「不安全」：太抽象了——重写时具体到「CPU 检查特权级，不通过就抛异常」。如果只写了「内核态权限高」：要补上「用户态怎么获得受控的、有限的访问」——那就是系统调用号。",
        },
        "hint3": "硬件层面，CPU 在每条指令执行前都检查特权级——用户态（DPL 3）的代码碰到内核段（DPL 0）会直接被拒绝。系统调用号让 CPU 知道「这是合法的跨级请求」，于是放行。三个词的因果关系由你自己说清。",
    },
    "lab3-full-depth-1": {
        "coach": {
            "why": "这一步比上一步要求更深：要解释清楚「特权级机制是怎么阻止的」。不是「我们规定不让跳」，而是 CPU 硬件每次访问内存都查 DPL——用户态访问内核地址 = 一般保护异常 = 进程被 kill。",
            "observe": "三个关键词在 Lab3 的角色：用户态（CPU 的 DPL=3 状态）、内核态（DPL=0）、系统调用号（用户态合法跨级的「编号」，由 eax 寄存器传递给 system_call）。",
            "act": "写 3 句话以上：① 直跳为什么不行（特权级硬件检查）；② 合法路径是什么（int 0x80 + 系统调用号 + sys_call_table）；③ 这种设计为什么必要（用户代码不可信，内核必须自己审查请求）。",
            "check": "你应该能说出：「不能直跳」不是软件约定，是 CPU 硬件强制——这正是 OS 安全模型的物理基础。",
            "repair": "如果你写得很泛：补上具体——「CPU 在每次内存访问/指令跳转时检查 DPL」「如果用户态代码碰到内核段会触发异常 13」「系统调用号是 eax 寄存器里的整数，由用户填好后 int 0x80 一起交给内核」。",
        },
        "hint3": "三个关键词围绕「硬件强制 + 受控通道」展开。用户态（受限）、内核态（特权）、系统调用号（合法穿越的编号）——把它们的关系写到「具体到寄存器/异常号」这种粒度，才说明你真的懂。具体写法你自己给。",
    },
    "lab3-reflect-summary": {
        "coach": {
            "why": "复盘要把「系统调用为什么必要 + 它怎么实现」固化下来。三句话的用途：第一句答驱动问题（说出受控入口的本质）、第二句标记最易混的边界（用户/内核态切换）、第三句给真实实验留具体证据（比如 eax 寄存器的值或 strace 输出）。",
            "observe": "驱动问题：「用户程序不能随便跳进内核，那它怎样安全地请求内核帮忙？」第一句直接回答：通过 int 0x80 + 系统调用号 + sys_call_table 这条受控通道。",
            "act": "三段：① 系统调用的完整路径（5 棒）；② 最易混的边界（用户态/内核态、call/int 0x80、函数指针/调用号）；③ 真实实验时第一个看的证据（strace 输出、eax 值、sys_call_table 内容）。",
            "check": "你应该能说出：以后调用失败时这份清单能直接告诉你「号对没对、表挂没挂、调用约定符不符」——三道检查解决 90% 的 Lab3 问题。",
            "repair": "如果三句话都很笼统：等于没写。把每句换成具体动作（grep 哪个文件、看哪个寄存器值、跑什么命令）。",
        },
        "hint3": "把这一关压成 3 句话：第一句给出 5 棒的简短链路（用户封装 → int 0x80 → system_call → sys_call_table → sys_xxx）；第二句指出最易混的「调用号 vs 函数指针」或「函数调用 vs 系统调用」；第三句留一个真实实验时第一个要看的证据（strace / 寄存器 / 表内容）。具体内容你自己来。",
    },
}


def main() -> None:
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    lab = next(lab for lab in data["labs"] if lab["id"] == "lab3")
    written = 0
    total = sum(len(p["steps"]) for p in lab["phases"])
    for phase in lab["phases"]:
        for step in phase["steps"]:
            craft = LAB3_HANDCRAFT.get(step["id"])
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
    print(f"已为 lab3 手写 {written}/{total} 步")


if __name__ == "__main__":
    main()
