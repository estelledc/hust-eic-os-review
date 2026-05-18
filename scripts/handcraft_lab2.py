#!/usr/bin/env python3
"""为 lab2「操作系统的引导」10 个 step 手写 coach 与第三层 hint。"""

from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "content" / "practice-labs.json"


LAB2_HANDCRAFT: dict[str, dict] = {
    "lab2-starter-map": {
        "coach": {
            "why": "刚开机时只有 BIOS，没有操作系统。Lab2 想让你看清「内核不是凭空跳起来的」——它是被一段段代码接力装入并启动的。这一步先确认你抓住了「接力」这个核心动作。",
            "observe": "正确选项明确说「一步步交给内核」——这是接力的关键描述。其它选项把这关误读成了别的实验：信号量是 Lab6、文件复制不是引导、C 函数调用是普通程序而不是冷启动。",
            "act": "选出唯一描述「控制权从 BIOS 一步步移交到内核」的那一项。",
            "check": "你应该能说出：本关研究的是「冷启动后控制权怎么走」。冷启动 = CPU 处于实模式、内存里只有 BIOS——任何 OS 代码都得自己装入。",
            "repair": "如果你选了「信号量排队」，是把 Lab6 的内容搬过来了；如果选「文件复制」，是把现代 OS 的高级动作放到了零起点；如果选「C 函数互相调用」，是忽略了「OS 还没起来时根本没有 C 运行时」。",
        },
        "hint3": "关键词是「一步步」——其它选项都缺这种「接力」感。其它选项里的术语（信号量、文件、C 函数）都属于已经有 OS 之后的世界，但 Lab2 在 OS 还没起来时——找出那条描述「冷启动到内核就绪」的话，但请用你自己的话复述一遍。",
    },
    "lab2-prepare-choice": {
        "coach": {
            "why": "bootsect 是接力的「第一棒」，只有 512 字节。它不可能是完整内核（容不下），也不可能是用户态程序（OS 还没起来）。这一步在排除两类越级的误解：把它当终点 / 把它当顶层用户视角。",
            "observe": "load-next 抓住了 bootsect 的核心职责——把后面的 setup/system 装入。final-kernel 把它当完整内核（数量级错了几千倍），user-program 把它当用户态（顺序倒了——用户态要在内核就绪后才存在）。",
            "act": "选 load-next：bootsect 的工作就是「读后面的代码进内存，然后跳过去」。",
            "check": "你应该能说出：bootsect 是「装载器的装载器」——它本身很小，只够把更大的 setup 读进来，让接力继续。",
            "repair": "如果选了 final-kernel：你忽略了 bootsect 只占 512 字节的物理限制——一个完整内核装不下。如果选了 user-program：你跳过了「OS 还没起来怎么会有用户态」这个时序问题。",
        },
        "hint3": "bootsect 的物理限制是 512 字节（一个磁盘扇区）——这个尺寸只够做一件事，就是「把更大的代码读进来再跳过去」。在选项里找符合这种「装载器的装载器」角色的那一句，但具体为什么不是其他两个，请你自己解释。",
    },
    "lab2-prepare-trace": {
        "coach": {
            "why": "引导阶段的因果链非常严格：每一棒都为下一棒准备运行环境。常见错排是把「进入保护模式」放在 head.s 之后或 setup 之前，但实际是 setup 收集机器信息后切到保护模式，head.s 才能用 32 位代码运行。",
            "observe": "5 个动作的状态变化：BIOS 加载 bootsect（CPU 跳到 0x7C00）→ bootsect 读取 setup（更多代码进内存）→ setup 收集机器参数（拿到内存大小、显卡等状态）→ 进入保护模式（CPU 模式从 16 位实模式切到 32 位保护模式）→ head.s 准备内核运行（建初始页表、跳到 main）。",
            "act": "把「BIOS 加载 bootsect」拖到第一位、「head.s 准备内核运行」拖到最后；中间 3 步按「装入更多代码 → 收集机器信息 → 切 CPU 模式」排序。",
            "check": "你应该能说出：保护模式的切换必须在 setup 之后、head.s 之前——因为 setup 是 16 位实模式代码，head.s 是 32 位保护模式代码，模式切换是它们之间的桥。",
            "repair": "如果你把「进入保护模式」放在 head.s 之后：head.s 就跑不起来了，因为它是 32 位代码却在 16 位环境里。如果放在 setup 之前：setup 用 BIOS 中断收集机器信息，BIOS 中断只在实模式可用——切早了 setup 就坏了。",
        },
        "hint3": "用「下一棒需要什么状态」反推：head.s 是 32 位代码 → 必须先在保护模式；setup 用 BIOS 中断 → 必须还在实模式；bootsect 装 setup → 自己得先被装入。把这三条因果接起来，顺序就出来了，但请你自己确认。",
    },
    "lab2-observe-diagnose": {
        "coach": {
            "why": "「想观察 bootsect 但只在内核里看到输出」——这是 OS 实验里的经典错觉。原因不是 bootsect 没跑，而是你的观察点（比如 printk）放在了 bootsect 看不到的位置。这一步在练「观察点要和被观察对象同处一个阶段」。",
            "observe": "wrong-stage 直指核心：你的观察工具（比如 printk）是内核的设施，bootsect 阶段还没有内核——所以 bootsect 的状态根本不会被这种观察点记录。其它两个选项把锅扣在了无关的事情上。",
            "act": "选 wrong-stage：观察点必须用 bootsect 阶段能用的方式（直接写显存、BIOS 0x10 中断打印），不能用还没存在的内核 API。",
            "check": "你应该能说出：观察点必须在被观察阶段「能跑」的代码里——bootsect 阶段没有 printk，所以 printk 看不到 bootsect。",
            "repair": "如果选了 wrong-report-title 或 wrong-semaphore：那是与现象无关的因素。回到现象：你看不到 bootsect 输出，是因为输出这个动作本身没在 bootsect 阶段执行——必须在 bootsect 自己的代码里直接打印（比如 BIOS int 0x10）。",
        },
        "hint3": "观察一个阶段必须用那个阶段「能跑」的工具：bootsect 用 BIOS 中断或直接写显存，head.s 之后才能用更高级的工具。看不到输出不一定是没跑，更常见是观察点放错了——但具体是哪类放错的，请用你自己的话说出来。",
    },
    "lab2-observe-fill": {
        "coach": {
            "why": "bootsect 和保护模式是 Lab2 的两个核心术语：一个是「接力第一棒的代码名字」，一个是「让 32 位内核能运行的 CPU 模式」。这一步在用最少的字让你确认这两个名字和它们的角色对得上。",
            "observe": "第一空指向「BIOS 读入的第一段」——这个角色只对应 bootsect（占 512 字节、引导扇区）。第二空指向「setup 之后切的 CPU 模式」——这是从实模式（16 位）切到保护模式（32 位）的状态变化。",
            "act": "first 空填 bootsect，mode 空填「保护模式」（也接受 protected）。",
            "check": "你应该能说出：bootsect 是「人」（一段代码），保护模式是「环境」（CPU 的运行模式）——两者属于不同范畴，不会混淆。",
            "repair": "如果第一空填了 setup：setup 是 bootsect 之后被装入的，不是「BIOS 直接读入的」。如果第二空写了「实模式」：那是 BIOS 阶段的状态，不是 setup 之后切去的目标。",
        },
        "hint3": "BIOS 在加电后只会自动读一个扇区到 0x7C00 ——这个扇区的代码就是第一空答案。CPU 启动时是 16 位实模式（兼容老 PC），要跑 32 位内核必须切到第二空的状态——但请用术语本身写答案。",
    },
    "lab2-operate-command": {
        "coach": {
            "why": "和 Lab1 的 make 不同：Lab2 是单独编译 boot/ 目录下的引导代码，所以 cd 要进 boot 子目录。这一步在让你区分「整体 make」和「针对引导的 make」——位置错了产物就不对。",
            "observe": "starter 第一条 cd oslab/linux-0.11/boot 把你站到了引导代码的目录。这里能看到 bootsect.s、setup.s、head.s 的源文件——下一条 make 才是只编译这一段。",
            "act": "在第一条之后追加 make → cd ../../ → ./run。注意 cd ../../ 是退两层（boot → linux-0.11 → oslab），因为 ./run 在 oslab 根。",
            "check": "你应该能说出：每条命令对应一次状态变化——cd 改当前目录、make 改 boot/ 下的产物（生成 bootsect 镜像）、cd ../../ 退到 oslab、./run 启动 Bochs 加载新镜像。",
            "repair": "如果只 cd .. 一层：你停在了 linux-0.11，./run 找不到。如果省略 cd 直接 ./run：在 boot/ 目录里没有 run 脚本。如果 make 漏了：./run 启动的还是老引导代码——和你的修改无关。",
        },
        "hint3": "这次的 cd 进了 boot 子目录而不是 linux-0.11 顶层，所以最后 cd 要退两层而不是一层。每条命令的前提是它的前一条命令产生了正确状态——具体顺序由你写出来。",
    },
    "lab2-operate-code": {
        "coach": {
            "why": "setup 阶段是观察寄存器状态的最后一个「实模式机会」——一旦切到保护模式，很多 BIOS 调用就用不了。在 setup 里打印寄存器值是引导调试的标准动作。这一步让你把这个观察意图写到代码里。",
            "observe": "starter 注释已经点出「在 setup 阶段观察寄存器」。三个关键词的含义：print（打印动作）、register（被观察对象）、setup（被观察的阶段）——三者必须同时出现，才说明你抓住了「在哪里、看什么、用什么手段」。",
            "act": "在 print_hex 调用里写出 register 名（比如 ax 或者直接注释「register from setup」），三个关键词都要出现在你的片段里。",
            "check": "你应该能说出：观察寄存器状态最好的时机是模式切换之前——切换之后寄存器值会被 head.s 重写，再看就看不到原始机器信息了。",
            "repair": "如果你写了 print 但没写 register：你观察了「打印这个动作」但没指明对象；写了 register 但没写 setup：你不清楚在哪个阶段观察。三个词缺一就缺一节信息。",
        },
        "hint3": "调试引导时，最常做的事是「在切到保护模式前打印寄存器值看 BIOS 给了什么」。三个关键词分别对应：观察手段、观察对象、观察阶段——把它们用一句话串起来即可，但句子要能说明你为什么选这个时机。",
    },
    "lab2-operate-explain": {
        "coach": {
            "why": "引导是「不能跳步的接力」——上一棒没跑完，下一棒拿不到正确状态。理解这一点的方式不是死记顺序，而是说出「每棒为下棒准备了什么」：BIOS 把 bootsect 装到内存、bootsect 把 setup 装入、setup 收集机器信息并切模式。",
            "observe": "三个关键词是接力的前三棒。失败时倒着追：内核不工作 → 看 head.s 是否进入 → 看 setup 是否完成 → 看 bootsect 是否被加载 → 看 BIOS 启动是否正常。每一节都靠前一节交付的状态。",
            "act": "写 2-3 句话，按「BIOS 给了 bootsect 什么 → bootsect 给了 setup 什么 → setup 给了内核什么」的顺序，三个关键词全用上。",
            "check": "你应该能说出：每一棒要么完整跑完并交出预期状态，要么根本没跑——没有「跑了一半」这种中间态可以让下棒可靠继续。",
            "repair": "如果你只写了三个词但没说「谁给谁什么」：那是堆砌不是解释——重写时给每一对相邻的关键词加一句「上一棒交付的是 X，没有 X 下一棒就 Y」。",
        },
        "hint3": "三个词不是平级的标签，而是接力的三棒。BIOS 交付了「bootsect 在内存里」这个状态，bootsect 交付了「setup 在内存里」，setup 交付了「机器信息+保护模式」。任意一节断了下一节就拿不到必需状态——但请你自己写完整因果。",
    },
    "lab2-full-depth-1": {
        "coach": {
            "why": "这一步要求更深：不仅说出「不能跳」，还要说出「每棒至少负责什么」。这是把「BIOS、bootsect、setup」从模糊概念变成可名状的接力关系。能写清楚的人后面看 boot.s 源码会非常顺。",
            "observe": "三棒各负责一种状态准备：BIOS 负责让 bootsect 这 512 字节进内存（物理动作）；bootsect 负责把 setup 装入并跳过去（自己只是过路人）；setup 负责收集机器信息并切到保护模式（最关键的一棒）。",
            "act": "每个关键词配一句具体职责。例如：BIOS 把磁盘第一扇区读到 0x7C00；bootsect 把后续若干扇区装入并 jmp 到 setup；setup 调 BIOS 中断拿内存大小、显卡参数，然后切到保护模式。",
            "check": "你应该能说出：合并任何两棒都会让职责丢失——BIOS+bootsect 合并就没人去装 setup，bootsect+setup 合并就装不下 setup 那么多代码。",
            "repair": "如果你写得太抽象（比如「BIOS 启动机器」「bootsect 引导」）：那等于没说。重写时给每棒配一个具体动作（读哪个扇区、跳哪个地址、收集什么信息）。",
        },
        "hint3": "把每棒的职责具体到「读什么/装什么/收集什么」级别。BIOS 的动作具体到字节（读一个扇区到 0x7C00），bootsect 的动作具体到跳转地址，setup 的动作具体到「BIOS 中断 + 切模式」。这种具体度才说明你真的懂——具体写法你自己给。",
    },
    "lab2-reflect-summary": {
        "coach": {
            "why": "复盘是把「冷启动接力」固化成你以后能复用的检查清单。三句话对应三个用途：第一句答驱动问题、第二句标记最容易翻车的边界（实模式/保护模式切换、装载器/被装载者）、第三句给真实实验留一个具体证据。",
            "observe": "驱动问题：「控制权怎样从 BIOS 一棒一棒交给 Linux 0.11 内核？」你的第一句要直接回答它，不要绕弯。可以是：BIOS 加载 bootsect → bootsect 装 setup → setup 切保护模式 → head.s 进入内核 main。",
            "act": "三段：① 接力链路（4-5 棒）；② 最易混的边界（实/保护模式切换、装载器/被装载者）；③ 真实实验时第一个看的证据（比如串口输出第一行来自哪一棒）。",
            "check": "你应该能说出：以后调试引导问题时，这份清单能直接告诉你「先看哪一棒、再看哪一棒」——不用每次重新推导。",
            "repair": "如果三句话都很笼统：等于没写。把每句改成具体动作（看哪个文件、看哪条输出、跑什么命令）。",
        },
        "hint3": "把这一关压成 3 句话：第一句写出 4-5 棒接力的简短链路；第二句写出最容易混淆的「实模式 vs 保护模式」或「装载器 vs 被装载者」；第三句给未来真实实验时第一个要查的证据。每句要在三个月后能直接复用——内容你自己来。",
    },
}


def main() -> None:
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    lab = next(lab for lab in data["labs"] if lab["id"] == "lab2")
    written = 0
    total = sum(len(p["steps"]) for p in lab["phases"])
    for phase in lab["phases"]:
        for step in phase["steps"]:
            craft = LAB2_HANDCRAFT.get(step["id"])
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
    print(f"已为 lab2 手写 {written}/{total} 步")


if __name__ == "__main__":
    main()
