#!/usr/bin/env python3
"""为 lab1 的 9 个 step 手工撰写 coach 与第三层 hint。

每个 step 的 coach 5 维必须引用本 step 自己的具体细节
（具体选项 / 具体命令 / 具体术语），而不是套用 lab 级模板。
"""

from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "content" / "practice-labs.json"


# 每个 step 独立撰写：why / observe / act / check / repair + 第三层 hint
LAB1_HANDCRAFT: dict[str, dict] = {
    "lab1-starter-map": {
        "coach": {
            "why": "OS 实验里，初学者最常迷路的不是某行代码，而是「我以为 Bochs 跑的就是我刚改的源码」。这一关的所有后续动作都建立在这条认知上：源码不会自动出现在 Bochs 里。先认这一点，再做任何事。",
            "observe": "看四个选项，三个错的各代表一种典型陷阱：被术语吓到（选「记目录名」）、被旁观知识替代（选「调度算法」）、把表象当成本质（选「多输出几行」）。只有 plain 选项点出了「源码 → Image → Bochs」的核心链路。",
            "act": "选出唯一指出「证明改动进了 Image」的那一项；其它三项都把这关的目的弄丢了。",
            "check": "你应该能说出：本关不是练命令，是在建立证据意识——任何修改都要能在 Bochs 里被看见，否则就当没改。",
            "repair": "如果你选了「记目录名」，说明你被表面动作吸引；如果选了「调度算法」，说明你跳过了 Lab1 直接想后面；如果选了「多输出字」，说明你把现象当成了目的。回到题目：这关在解决「证据」问题。",
        },
        "hint3": "正确选项里有一个关键短语：「证明 Bochs 跑到了新 Image」。其它选项都缺这条「证明」的因果——找出唯一同时提到「改源码」和「Bochs 验证」的那一句，但选完后请用你自己的话复述一遍。",
    },
    "lab1-prepare-choice": {
        "coach": {
            "why": "工作流的方向是：宿主机做编辑+构建，模拟机只做加载+运行。两个错误选项都把这个方向反过来——以为 Bochs 能自动读源码、自动编译。这是「以为模拟器无所不能」的初学者陷阱。",
            "observe": "edit-run-directly 暗示「改完就好」，省略了构建；bochs-builds-source 把 Bochs 当成 IDE。两者都把宿主机的工作甩给了模拟机。正确选项 edit-build-run 明确写出三个动作的接力。",
            "act": "选出按「编辑 → 构建 → 启动」排好顺序、且把动作分配给正确角色的选项。",
            "check": "你应该能说出：宿主机的职责是改源码 + make；Bochs 的职责是加载 make 产生的 Image。这两件事不能合并，也不能换人做。",
            "repair": "如果你选了 edit-run-directly，是把构建步漏掉了——回想一下：源码是文本，CPU 不能直接执行文本。如果选了 bochs-builds-source，是把构建职责安到了模拟机上——Bochs 是「电脑模拟器」，不是「编译器」。",
        },
        "hint3": "三个选项里只有一个把「编辑、构建、启动」三步分别说出来；另两个或省略中间步、或把构建甩给 Bochs。挑出明确写出 make 这步的那一项——但你也要能解释为什么这一步不能跳。",
    },
    "lab1-prepare-trace": {
        "coach": {
            "why": "排序错的最常见模式是把「准备镜像文件交换」放最后，以为它是观察的一部分。其实它是「让 Bochs 拿到新 Image」的桥梁，必须在启动 Bochs 之前。这一步要看清「数据如何从宿主机传到模拟机」。",
            "observe": "观察 5 个动作之间的因果状态：「修改源码」改的是宿主机文件状态，「编译 Image」改的是构建产物状态，「准备镜像文件交换」改的是 Bochs 能不能读到新 Image，「启动 Bochs」改的是模拟器的运行状态，「在 Linux 0.11 中验证」是最终结果。每相邻两步必须前者改完后者才有意义。",
            "act": "把「修改源码」拖到第一位，「验证」拖到最后；中间三步按「先生成产物、再让模拟机找到、最后启动」排序。",
            "check": "你应该能说出：每一步如果不发生，下一步就没有意义——没改源码就没必要 make；没 make 就启动 Bochs 等于跑老 Image；没准备镜像交换 Bochs 就找不到新 Image。",
            "repair": "如果你把「准备镜像文件交换」放在「启动 Bochs」之后，问自己：Bochs 启动时它读哪里？读不到新 Image 就还是老的。把它移到「编译 Image」之后、「启动 Bochs」之前。",
        },
        "hint3": "对每两个相邻节点问：「上一步如果没做，下一步还能做吗？」例如「编译 Image」和「准备镜像文件交换」——没编译，要交换什么呢？这条因果链能把所有节点定位清楚，但最终顺序请你自己验证。",
    },
    "lab1-observe-diagnose": {
        "coach": {
            "why": "「改了没变化」是 OS 实验最频繁的错觉。错的诊断方向有两类：往美学/界面上找（改字体），或者干脆放弃验证（不启动 Bochs）。正确的方向永远是回到证据链：Image 是不是真的更新了。",
            "observe": "三个选项里，rebuild-image 把你拉回到证据：它要求你看 Image 文件本身和 Bochs 启动日志这两条状态。change-font 把现象引向无关维度，skip-bochs 干脆放弃观察——后两个都不收集任何证据，所以不可能是真诊断。",
            "act": "选 rebuild-image：先看 Image 时间戳和 Bochs 启动日志，再判断到底跑没跑新内核。",
            "check": "你应该能说出：现象不变时，先怀疑「我改的源码到底有没有被 make」，而不是怀疑代码逻辑。这是诊断的第一性步骤。",
            "repair": "如果选了 change-font：你在治症状不治病。如果选了 skip-bochs：你放弃了唯一的验证手段。回到链路上：源码 → make → Image → Bochs。任何一节断了，结果就不变——逐节查。",
        },
        "hint3": "「改了没变化」有三种典型原因：①没 make 生成新 Image；②make 了但 Bochs 启动的还是老镜像；③改的代码不在编译路径里。三种都指向同一个第一步：先确认 Image 真的更新了——但具体怎么确认要靠你自己说。",
    },
    "lab1-observe-fill": {
        "coach": {
            "why": "术语贴错最常见：把 Image 说成「Bochs」、把 Bochs 说成「内核」。这一步在用最短的方式让你区分「成品」和「运行成品的机器」——这两个东西在 Lab1 之后会一直纠缠出现。",
            "observe": "两个空各对应一种角色：「Bochs 加载的内核成品」是被加载者（=Image），「运行 Linux 0.11 的模拟电脑」是加载者（=Bochs）。提示语 placeholder 已经把答案写出来了，但你要理解为什么是这样。",
            "act": "在 kernel 空填 Image，在 simulator 空填 Bochs。",
            "check": "你应该能说出：Image 是文件（启动映像），Bochs 是程序（模拟硬件）。两者的关系是「Bochs 加载并运行 Image」——一物一名，绝不混用。",
            "repair": "如果填反了：你把「成品」和「运行成品的机器」搞混了。类比：电影是 Image（DVD 文件），DVD 播放机是 Bochs（机器）。播放器不是电影，电影也不是播放器。",
        },
        "hint3": "类比一下：Image 像 DVD 光盘上的电影文件，Bochs 像 DVD 播放器。光盘不会自己播放，播放器没有光盘也不知道放什么。两个空填的是这两种角色——但请用术语本身写答案，不要写类比词。",
    },
    "lab1-operate-command": {
        "coach": {
            "why": "命令的顺序就是状态变化的顺序。这一步要练的不是「记住四条命令」，而是看出每条命令在改什么状态——cd 切目录、make 生成 Image、cd .. 退到 oslab 根、./run 启动 Bochs。少一条或顺序错都会让链路断。",
            "observe": "starter 第一条 cd oslab/linux-0.11 把你的当前目录状态切到源码目录。从这条命令的结果看：你现在能看到 Makefile 和 boot/ 等子目录——这说明你站在了能 make 的位置上。下一条必须利用这个状态。",
            "act": "在第一条之后追加：make → cd .. → ./run。每条命令独占一行。",
            "check": "你应该能说出：cd 改的是「我现在站在哪个目录」，make 改的是「Image 文件是新还是旧」，./run 改的是「Bochs 是否启动」——三种状态各对应一条命令。",
            "repair": "如果 make 漏了：你跳过了「把源码变成 Image」这一步，./run 启动的还是老 Image。如果 cd .. 漏了：./run 找不到，因为 run 脚本在 oslab/ 而不在 oslab/linux-0.11/ 里。如果顺序乱了：状态变化的因果就接不上。",
        },
        "hint3": "命令分两类：移动光标的（cd）和改变文件/进程的（make、./run）。第一条给你了，下一条要在源码目录里产生新 Image，再下一条要回到能启动 Bochs 的位置，最后启动它——具体写法你自己来。",
    },
    "lab1-operate-code": {
        "coach": {
            "why": "代码片段不是让你写完整逻辑，而是让你用注释表达「三个对象的关系」。如果你能在两行注释里把 linux-0.11、Image、Bochs 的关系讲对，说明你已经把整个加工线放进了脑子里。",
            "observe": "starter 已经写了一句「linux-0.11 源码经过 make 生成 Image」——你需要补的是 Bochs 怎么进来。Bochs 的角色不是编译，是「加载 Image」。",
            "act": "在 starter 注释后追加一句话，把 Bochs 的角色写出来——例如 Bochs 加载 Image 启动 Linux 0.11，让三个关键词都自然出现。",
            "check": "你应该能说出：linux-0.11（源码）+ Image（构建产物）+ Bochs（加载器）三者构成完整链路，缺一不可。",
            "repair": "如果你只写了 Bochs 但没说它「加载 Image」：你把 Bochs 当成抽象工具了。如果你写了 Image 但没接 Bochs：你把构建和运行断开了。三个关键词必须在一句话里有因果关系，不是并列堆砌。",
        },
        "hint3": "注释只需要把三件事的因果说清：linux-0.11 是输入、Image 是中间产物、Bochs 是消费者。一句「Bochs 不读源码，只加载 Image」就足够触发关键词检查——但你写的句子要能让别人读懂这条因果。",
    },
    "lab1-operate-explain": {
        "coach": {
            "why": "调试时最容易凭直觉乱猜。这一步在练「按链路找断点」：从源码到 Bochs 之间有四节，任何一节断了现象都不会变。能用「重新编译 / Image / Bochs」三个词组织出诊断顺序，说明你已经把链路内化了。",
            "observe": "三个关键词是按因果排的：源码改了 → 重新编译 → 产生新 Image → Bochs 加载新 Image。诊断时反着走：先看 Bochs 加载的是不是新 Image，再看 Image 时间戳，再确认是否真的 make 了。",
            "act": "写 2-3 句话，按「先看 X，再看 Y，最后看 Z」的顺序，把三个关键词都用上。可以是「先看 Bochs 启动日志确认加载了哪个 Image，再看 Image 文件时间戳，最后回到源码目录确认是否重新编译」。",
            "check": "你应该能说出：诊断顺序不能从源码端开始，而要从「我看到的现象」端开始往回追——因为终点（Bochs）才是产生现象的地方。",
            "repair": "如果你写得太短没覆盖三个词：你跳过了链路的某一节，下次现象不变时你也会跳过那一节。如果三个词都用了但没顺序：那是堆砌不是诊断——重写时给每个词配一句「先看 / 再看 / 最后看」。",
        },
        "hint3": "诊断不是把三个词往一起堆，而是写出顺序：从「我现在看到的」回溯到「我可能漏的」。Bochs（终点）→ Image（中间产物）→ 重新编译（源头动作）——每步都问「这一节有没有出问题」，但具体怎么写让用户能跟着做，靠你自己。",
    },
    "lab1-reflect-summary": {
        "coach": {
            "why": "复盘不是写感想，是给「未来要做真实实验的自己」留一份检查清单。三句话对应三种用途：第一句答驱动问题（说出方法）、第二句标记最容易翻车的地方、第三句给未来的自己一个具体动作。",
            "observe": "驱动问题已经印在 prompt 里了：「我改了源码以后，怎样确认 Bochs 启动的确实是新构建出来的 Linux 0.11？」——你的第一句话直接回答它即可。",
            "act": "写三段：① 我会怎么确认 Bochs 跑了新内核（Image 时间戳 + Bochs 启动输出 + 一个可观察现象）；② 最容易混的边界（宿主 vs 模拟、源码 vs Image）；③ 真实实验时第一个看的证据（Image 是否更新）。",
            "check": "你应该能说出：每次现象不变时，复盘里这份清单能直接复用——不用再从头思考。",
            "repair": "如果三句话都写得很泛：那等于没写。把每句换成具体动作（看哪个文件、看哪行输出、跑什么命令），下次才能用。",
        },
        "hint3": "把这一关的所有内容压成 3 句话：第一句回答「怎样证明 Bochs 跑了新内核」；第二句指出最容易混淆的边界；第三句留一个未来真实实验时第一个要查的证据。每句话都要具体到能在三个月后看懂——但内容由你来写。",
    },
}


def main() -> None:
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    lab1 = next(lab for lab in data["labs"] if lab["id"] == "lab1")
    written = 0
    for phase in lab1["phases"]:
        for step in phase["steps"]:
            craft = LAB1_HANDCRAFT.get(step["id"])
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
    print(f"已为 lab1 手写 {written}/9 步")


if __name__ == "__main__":
    main()
