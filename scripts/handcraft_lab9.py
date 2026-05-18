#!/usr/bin/env python3
"""为 lab9「proc 文件系统的实现」10 个 step 手写 coach 与第三层 hint。"""

from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "content" / "practice-labs.json"


LAB9_HANDCRAFT: dict[str, dict] = {
    "lab9-starter-map": {
        "coach": {
            "why": "/proc 看起来像普通目录、cat /proc/cpuinfo 看起来像读普通文件——但内容不来自磁盘。Lab9 的核心想让你看清「同样的 read 接口可以背靠完全不同的数据源」。这一步先确认你抓住了「文件接口 + 内核状态」的双面性。",
            "observe": "正确选项点出「文件接口读内核实时状态」——这就是 proc 的本质。其它选项都跑题：P/V 同步是 Lab6、创建普通文件没意义、BIOS 启动顺序是 Lab2。",
            "act": "选出唯一同时提到「文件接口」和「内核实时状态」的那一项。",
            "check": "你应该能说出：proc 是「假装成文件的内核数据导出通道」——用户用熟悉的 read 接口，但取到的不是磁盘字节，而是内核当下的状态。",
            "repair": "如果选了 P/V：那是 Lab6。如果选了「创建普通文件」：那忽略了 proc 文件没有磁盘存储这一关键差别。如果选了 BIOS：那是 Lab2 范畴。",
        },
        "hint3": "Lab9 的核心是「文件接口」（用户视角不变）+「内容动态生成」（内核视角的特殊点）。其它选项都没有同时谈这两件事。找出唯一描述「假装成文件的内核状态导出」的那一句，但请你自己解释为什么这个抽象很有用。",
    },
    "lab9-prepare-choice": {
        "coach": {
            "why": "「proc 文件 = 磁盘文件」是初学者的典型误解。其实 proc 文件的内容在 read 那一刻才由内核函数生成——它没有「保存」在任何地方。这一步要排除「磁盘说」和「只是名字特殊」两种错误模型。",
            "observe": "generated 选项点出真正机制：内容由内核 read 回调动态生成。always-disk 是错的——proc 没有磁盘备份。only-name 也错——内容来源完全不同（磁盘 vs 内核状态），不只是名字。",
            "act": "选 generated：proc 节点的 read 回调每次被调用都执行一次内核函数、把当前状态格式化成文本返回。",
            "check": "你应该能说出：proc 文件的「内容」不是预先存在的字节流，是「read 时计算出来的字符串」——所以它能反映实时状态。",
            "repair": "如果选了 always-disk：那 proc 怎么反映「当前进程列表」这种实时数据？磁盘字节没人去更新它。如果选了 only-name：你忽略了「内容是 read 时算出来的」这一根本机制。",
        },
        "hint3": "proc 文件没有磁盘扇区——你 ls 它显示大小通常是 0 或固定数（驱动报的），但 cat 它能拿到实时数据。这种矛盾说明内容不是从磁盘读的，而是 read 时由内核函数生成的。具体为什么 always-disk 不行请你自己解释。",
    },
    "lab9-prepare-trace": {
        "coach": {
            "why": "proc 的因果链：用户 open → VFS 路由到 proc → read 触发回调 → 回调读内核状态 → 格式化文本 → 返回用户缓冲区。常见错排是把「读内核状态」放在 VFS 之前——但 read 必须先经过 VFS 找到处理函数才能调到那个回调。",
            "observe": "5 个动作的状态变化：用户进程 open proc 节点（VFS 创建文件描述符）→ VFS 找到 proc 处理函数（在文件操作表里查到 proc 自己的 read 函数）→ read 时读取内核状态（回调跑起来访问内核数据）→ 格式化为文本（把数据转成字符串）→ 返回用户缓冲区（拷到用户态）。",
            "act": "把「用户进程 open proc 节点」拖到第一位、「返回给用户缓冲区」拖到最后；中间 3 步按「VFS 路由 → 读状态 → 格式化」排序。",
            "check": "你应该能说出：proc 的特殊性体现在「VFS 之后」——VFS 把它当普通文件处理，但 proc 的 read 函数指针指向的是状态读取代码而不是磁盘读取代码。",
            "repair": "如果你把「读内核状态」放在「VFS 找到 proc 处理函数」之前：那时根本不知道要读什么状态——VFS 才是把请求路由到具体回调的关键。如果把「open」放在中间：那文件描述符还没建立，后续 read 没有上下文。",
        },
        "hint3": "proc 利用了 VFS 的统一接口——前两步（open + VFS 路由）和普通文件一致，差别从第三步开始（read 时不读磁盘而是读内核状态）。这条因果链由你自己确认，但记住：VFS 是分流器，不是数据源。",
    },
    "lab9-observe-diagnose": {
        "coach": {
            "why": "「proc 输出不变」是 Lab9 经典 bug——往往是 read 回调被写成「return strcpy(buf, \"hello\")」这种静态字符串，根本没读内核状态。这一步在让你识别「现象指向 read 回调实现」而非别的子系统。",
            "observe": "dynamic-state 选项点出 proc 失效的真因：read 回调没读实时状态。wrong-pv-order 是 Lab6 范畴、wrong-stage 是 Lab2 范畴——和 proc 输出无关。",
            "act": "选 dynamic-state：去看 proc_read 回调函数，里面到底有没有访问内核数据结构（比如 task list、free memory），还是只是 sprintf 一个固定字符串。",
            "check": "你应该能说出：proc 输出永远不变 = read 回调里没有读任何动态数据 = 等于一个静态文件。修复方法是让回调真正访问内核当前状态。",
            "repair": "如果选了 wrong-pv-order 或 wrong-stage：那是别的实验的范畴。回到 Lab9 的具体问题：proc 文件的内容来自 read 回调——回调如果不读实时状态，输出当然不会变。",
        },
        "hint3": "proc 输出不变的诊断：先看 read 回调实现——里面是否调用了内核里返回当前状态的函数（current 进程、jiffies、空闲内存等）。如果只有静态字符串，那它就退化成普通文件了。具体怎么改由你来。",
    },
    "lab9-observe-fill": {
        "coach": {
            "why": "虚拟文件和内核状态是 Lab9 的两个核心名字——一个描述 proc 节点的本质（看起来像文件、实际不是），一个描述它的真正数据来源（内核内部数据结构）。两个名字定位 proc 的「假身真心」。",
            "observe": "观察两个空对应的概念：第一空指向「看起来像文件、实际内容不在磁盘」（这是虚拟文件 / virtual file）；第二空指向「proc read 应该取的数据」（这是内核状态 / kernel state）。两者一个是表象、一个是真相。",
            "act": "virtual 空填「虚拟文件」（也接受 virtual），source 空填「内核状态」（也接受 kernel）。",
            "check": "你应该能说出：proc 是虚拟文件的典型——文件接口是真的（用 open/read），文件内容是虚的（来自内核状态而非磁盘）。",
            "repair": "如果第一空填了「特殊文件」：那是模糊词，不能区分 proc 和别的东西（比如设备文件也是「特殊」的）。如果第二空填了「磁盘」：那直接错了——proc 内容根本不在磁盘上。",
        },
        "hint3": "Lab9 用两个名字解决两个问题：proc 是什么样的对象（虚拟文件——表面是文件接口）、它的内容从哪来（内核状态——内部数据结构）。两个空各占一个。具体术语请你写。",
    },
    "lab9-operate-command": {
        "coach": {
            "why": "Lab9 修改的是 fs/（文件系统代码），不是 kernel/ 也不是 mm/——这反映了 proc 是文件系统层的扩展。所以 cd 进 fs 子目录局部 make。./run 后接 proc-demo 启动观察程序——它会 cat 几个 proc 节点看动态内容。",
            "observe": "starter 第一条 cd oslab/linux-0.11/fs 切到文件系统目录。下一条 make 编进 proc 文件系统的 read 回调修改。再 cd ../../ 退两层，最后 ./run proc-demo 加载观察脚本——观察程序会 cat /proc/xxx 多次看输出是否变化。",
            "act": "在第一条之后追加 make → cd ../../ → ./run proc-demo。",
            "check": "你应该能说出：fs 目录是 Lab9 的修改重点——这反映 proc 属于文件系统子系统，而不是调度（kernel）或内存（mm）。",
            "repair": "如果 cd 进的是 kernel：你修改了调度代码而不是文件系统代码——proc 的 read 回调没被改，./run 看不到 Lab9 的现象。",
        },
        "hint3": "Lab9 的目录是 fs，体现 proc 属于文件系统。命令链结构和 Lab5/6/7 类似，但目录不同（fs 而不是 kernel/mm）、参数不同（proc-demo）。具体写法你自己来。",
    },
    "lab9-operate-code": {
        "coach": {
            "why": "proc_read 是 Lab9 的核心函数——它是被注册到 VFS 文件操作表里的回调。三个关键词分别对应：proc（被实现的子系统）、read（操作类型）、buf（输出位置——用户传进来的缓冲区指针）。三个缺一就不是合法的 read 回调。",
            "observe": "starter 给了 int proc_read(char *buf) 函数体注释「proc read formats kernel state into buf」。三个关键词的角色：proc（这是 proc 子系统的回调）、read（操作语义）、buf（数据写入目的地）。",
            "act": "保留 starter，确保 proc、read、buf 三个词在你的片段里都出现。可以在注释里补一行（比如 sprintf(buf, \"%s\\n\", get_kernel_state())）。",
            "check": "你应该能说出：proc_read 的工作 = 取内核状态 + 格式化 + 写到 buf。三段缺一不可——少了取状态就是静态、少了格式化就是裸数据、少了 buf 写入用户拿不到。",
            "repair": "如果只用了 proc 和 read 没用 buf：那是说了「这是 proc 的 read」但没说「写到哪里」——而 buf 是用户传进来的输出位置，不可省略。三个词必须齐。",
        },
        "hint3": "proc_read 的最简实现：从内核取一段状态（比如 current->state）、用 sprintf 格式化、写到 buf。三个关键词覆盖三段。把它们用一句注释串起来即可，但请用具体动词（read / format / write）。",
    },
    "lab9-operate-explain": {
        "coach": {
            "why": "「proc 输出不应该是固定字符串」是 Lab9 想让你内化的设计原则。三个关键词：虚拟文件（proc 的角色）、read（接口入口）、内核状态（数据来源）。三件事缺一就退化成普通文件——失去了 proc 存在的理由。",
            "observe": "三个词的因果：虚拟文件（不存磁盘所以可以动态）→ read（每次调用是一个生成时机）→ 内核状态（应该在每次 read 时被取一次）。如果固定字符串，三件事的协同就断了。",
            "act": "写 2-3 句话，按「虚拟文件可以动态生成 → read 是生成时机 → 内容必须来自内核状态」的顺序，三个词都用上。",
            "check": "你应该能说出：proc 的价值就在于「实时反映内核状态」——失去这个价值它就只是个奇怪的目录名而已。",
            "repair": "如果只列了三个词：补一句「proc 的实时性靠 read 时取内核状态来实现，固定字符串就丢了实时性」。",
        },
        "hint3": "三个关键词构成 proc 的设计三角：虚拟文件给「不存磁盘」的可能、read 给「每次重新生成」的时机、内核状态给「真实内容」的来源。三件事配合才有 proc 的实时性，但具体怎么写让用户能跟着想清楚由你来。",
    },
    "lab9-full-depth-1": {
        "coach": {
            "why": "这一步要解释为什么固定字符串等于 proc 失效。原因不在于「能不能编译」（写 sprintf 一句固定字符串完全合法），而在于「这违背了 proc 的设计意图」——proc 存在的理由就是导出实时状态，失去实时性就没有存在意义。",
            "observe": "三个关键词的角色：proc（被实现的子系统名）、read（每次访问的入口）、内核状态（必须在 read 时被读取的数据源）。三者的关系是「proc 在每次 read 时都要去读一次内核状态」——少任何一环就失去意义。",
            "act": "写 3 句话以上：① 固定字符串技术上能跑（语法正确）；② 但失去 proc 的设计意图（实时反映状态）；③ 正确做法是 read 回调里访问内核当下数据再格式化。",
            "check": "你应该能说出：proc 不是「另一种存文本的地方」，是「内核状态的标准化导出通道」——失去实时性就和普通文件没区别。",
            "repair": "如果你只说「不动态」：太抽象。补上具体——「这就和写一个 echo 'hello' 然后存到 hello.txt 等价了，根本没用上 proc 的能力」。",
        },
        "hint3": "proc 的价值不在「文件名特殊」，在「内容随状态变化」。固定字符串虽然能编译，但等价于退化成普通文件——proc 的所有特殊基础设施（VFS 注册、回调机制）都被浪费了。三个关键词必须连同「实时性」一起说，但具体写法你自己给。",
    },
    "lab9-reflect-summary": {
        "coach": {
            "why": "复盘要把「proc = 文件接口 + 动态内容 + 内核状态」沉淀下来。三句话用途：第一句答驱动问题（说出 proc 的双面性）、第二句标记最易混的边界（虚拟 vs 真实、文件接口 vs 文件来源）、第三句给真实实验留具体证据。",
            "observe": "驱动问题的回答模板：proc 文件被 VFS 当成普通文件路由；它的 read 回调访问内核数据结构；每次 read 都重新格式化当前状态——所以用户看到的是实时数据。",
            "act": "三段：① proc 的完整路径（VFS → read 回调 → 读内核状态 → 格式化 → 用户缓冲）；② 最易混的边界（文件接口 vs 文件来源、虚拟文件 vs 真实文件、固定内容 vs 动态生成）；③ 真实实验时第一个看的证据（多次 cat 同一节点看输出是否变、看 read 回调是否调了 get_xxx_state）。",
            "check": "你应该能说出：以后看任何「文件接口 + 动态内容」的设计（cgroups、sysfs、debugfs）都能立刻想到「这是 proc 模式的扩展」——本质都是用文件接口导出内核状态。",
            "repair": "如果三句话很泛：把每句换成具体动作（cat 多次 / 看回调实现 / 看 VFS 注册）。",
        },
        "hint3": "压成 3 句：第一句答「proc 怎样让用户看到内核实时状态」（VFS 路由 + 动态 read 回调）；第二句指出最易混的边界（文件接口 vs 数据来源）；第三句留真实实验时第一个要看的证据（多次 cat 看变化 / 看 read 回调实现）。具体内容你自己写。",
    },
}


def main() -> None:
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    lab = next(lab for lab in data["labs"] if lab["id"] == "lab9")
    written = 0
    total = sum(len(p["steps"]) for p in lab["phases"])
    for phase in lab["phases"]:
        for step in phase["steps"]:
            craft = LAB9_HANDCRAFT.get(step["id"])
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
    print(f"已为 lab9 手写 {written}/{total} 步")


if __name__ == "__main__":
    main()
