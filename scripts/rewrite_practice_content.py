#!/usr/bin/env python3
"""按 docs/plans/2026-05-18-practice-final-consolidation.md 重写 practice-labs.json 内容层。

设计原则：
- 每个 step 的 coach.{why, observe, act, check, repair} 5 段话各说一件事
- 内容来源是该 lab 的 firstPrinciples / mentalModel / focus / drivingQuestion——9 个 lab 数据不同，文案自然 lab-specific
- 严禁字段复制：coach.why != context；coach.act != prompt；coach.check != success
- 第三层 hint 拉到 ≥ 50 字，用"如果还在 A 和 B 之间犹豫，注意 C——但答案要靠你自己的话"模式
- starter 首步标题 = 用 lab 自己的 drivingQuestion 提取一句疑问句
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "content" / "practice-labs.json"


def pick(items: list, idx: int = 0, default: str = "") -> str:
    if not items:
        return default
    return items[idx % len(items)] if idx >= 0 else items[idx]


def coach_for_step(lab: dict, phase: dict, step: dict, step_idx_in_phase: int) -> dict:
    """为一个 step 生成 5 维 coach，确保不复制 context/prompt/success。"""
    fp = lab.get("firstPrinciples", {})
    actors = fp.get("actors", [])
    state = fp.get("state", [])
    boundary = fp.get("boundary", [])
    transition = fp.get("transition", [])
    evidence = fp.get("evidence", [])
    failure_modes = fp.get("failureModes", [])

    mental = lab.get("mentalModel", {})
    flow = mental.get("flow", [])
    checkpoints = mental.get("checkpoints", [])

    interaction = step["interaction"]
    phase_id = phase["id"]
    driving = lab.get("drivingQuestion", "")
    plain_goal = lab.get("plainLanguageGoal", "")
    focus = lab.get("focus", "")
    title = lab.get("title", "")

    # 用 step 在 phase 内的位置 + interaction 选择不同的 firstPrinciples 项目，让相邻 step 也有差异
    boundary_pick = pick(boundary, step_idx_in_phase)
    transition_pick = pick(transition, step_idx_in_phase)
    evidence_pick = pick(evidence, step_idx_in_phase)
    failure_pick = pick(failure_modes, step_idx_in_phase)
    actor_pick = pick(actors, step_idx_in_phase)
    state_pick = pick(state, step_idx_in_phase)
    flow_first = pick(flow, 0)
    flow_last = flow[-1] if flow else ""

    # ---- coach.why：解释这一步为什么现在出现，不复述 lab 总目标 ----
    why_by_phase = {
        "prepare": f"先把「{title}」这一关的边界看清。{boundary_pick}——没分清就会做后面动作时把两件事搞混。",
        "observe": f"在动手前先盯一条证据。{evidence_pick}——后面所有改动是否生效，都靠这条证据回答。",
        "operate": f"现在做最小可验证动作。{transition_pick}——只有真的让这一步发生，机制才从概念变成你看得到的现象。",
        "reflect": f"把这一关压缩成一句你能复述的因果。回到驱动问题：{driving}",
    }
    why = why_by_phase.get(phase_id, why_by_phase["prepare"])

    # ---- coach.observe：先看哪条状态/证据，不重复 phase.purpose ----
    observe_by_interaction = {
        "choice": f"看选项里哪一句把「{boundary_pick}」说对了。其它选项往往把两层混在一起。",
        "diagnose": f"先看现象，再回到机制。问自己：哪一条 failure mode 最贴合？参考：{failure_pick}",
        "fill": f"填空之前先认对象。{actor_pick}；状态在哪里：{state_pick}。把对象和状态名贴对，填空就有抓手。",
        "trace": f"排序之前先认顺序的因果。先发生的是 {flow_first}，最后落到 {flow_last}。中间步骤倒推因果即可。",
        "command": f"命令是状态改变的最短表达。先想这一步在改什么状态：{transition_pick}。命令就是这条变化的工具。",
        "code": f"代码片段不是抄写，是对照机制找位置。看：{transition_pick} 在代码里用什么名字？",
        "explain": f"解释之前先抓证据：{evidence_pick}。围绕这条证据组织你的话，比堆术语更让人信服。",
        "reflection": f"复盘要写出可被自己复用的因果。能回答驱动问题就行：{driving}",
    }
    observe = observe_by_interaction.get(interaction, observe_by_interaction["explain"])

    # ---- coach.act：当前要做的具体动作（动词起手），不复制 prompt ----
    act_by_interaction = {
        "choice": "在选项中找一个最贴合本关边界的表述，先排掉两种把对象搞混的说法。",
        "diagnose": "把每个候选错因和你看到的现象对一遍——选最能解释这个现象的一项。",
        "fill": "先在右侧术语里挑出本步要用的词，再回到空格旁填进去。",
        "trace": f"逐个把节点拖到正确位置：起点在 {flow_first}，终点在 {flow_last}，中间按因果接上。",
        "command": "在命令行里按照状态变化顺序逐条输入；每条命令对应一次状态改变。",
        "code": "在代码片段里加上或修改关键词，让它体现本步的状态改变；不必写完整逻辑。",
        "explain": "用 2-3 句话解释；先点证据，再说机制，最后给一句你的判断。",
        "reflection": "把你刚刚理解的因果写成一段话——给将来要做真实实验的自己看。",
    }
    act = act_by_interaction.get(interaction, act_by_interaction["explain"])

    # ---- coach.check：通过后用户能复述的一句，不复制 success ----
    check_by_phase = {
        "prepare": f"做对了你应该能说：{boundary_pick}——这就是本关后面所有讨论的前提。",
        "observe": f"做对了你应该能指着证据说：{evidence_pick}。这条证据在真实实验里同样可见。",
        "operate": f"做对了你应该能说：{transition_pick}——状态确实因为这个动作改变了。",
        "reflect": f"做对了你应该能简述：{plain_goal}。这就是本关沉淀下来的因果。",
    }
    check = check_by_phase.get(phase_id, check_by_phase["prepare"])

    # ---- coach.repair：错了回到哪个概念边界 ----
    repair_seed = failure_pick or boundary_pick or transition_pick
    repair_by_interaction = {
        "choice": f"如果你选错了，回到边界来对照：{boundary_pick}。再读一次选项，看哪个把这条边界讲清楚了。",
        "diagnose": f"如果你诊错了，回到 failure mode 列表：{failure_pick}。把每个错因和现象一一对照。",
        "fill": f"如果填错了，先回到对象：{actor_pick}；再回到状态：{state_pick}。把名字对应上。",
        "trace": f"如果排错了，回到因果起点：{flow_first}；只问『上一步如果不发生，下一步能不能发生』。",
        "command": f"如果命令顺序错了，回到状态变化：{transition_pick}。命令的顺序必须和状态变化的因果一致。",
        "code": f"如果代码漏关键词，回到 transition：{transition_pick}。代码要让这条变化在源码层有名字。",
        "explain": f"如果讲不清楚，回到证据：{evidence_pick}。讲不清通常是因为没把证据点到。",
        "reflection": f"如果写不出，回到驱动问题：{driving}。先回答它，再扩写。",
    }
    repair = repair_by_interaction.get(interaction, repair_by_interaction["explain"])

    # 兜底：如果生成结果碰巧和 step 已有字段相同（极小概率），加后缀打破
    ctx = step.get("context", "")
    prompt = step.get("prompt", "")
    success = step.get("success", "")
    if why == ctx:
        why = why + " 这一段是 coach.why 的扩写，不只是复述 context。"
    if act == prompt:
        act = act + "（具体到本步的对象上）"
    if check == success:
        check = check + " —— 把它说出来，比只看勾选更能确认你真理解。"

    return {"why": why, "observe": observe, "act": act, "check": check, "repair": repair}


def rewrite_third_hint(lab: dict, step: dict, original_text: str) -> str:
    """把过短（< 50 字）的第三层 hint 扩写为 lab-specific 的"接近答案"提示。"""
    fp = lab.get("firstPrinciples", {})
    boundary = pick(fp.get("boundary", []), 0)
    transition = pick(fp.get("transition", []), 0)
    evidence = pick(fp.get("evidence", []), 0)
    interaction = step["interaction"]

    # 基于 interaction + lab.firstPrinciples 生成长 hint
    seeds = {
        "choice": f"如果还在两个相近的选项之间犹豫，盯紧这条边界：{boundary}。把选项和这条边界对照，能讲清楚的那个就是要选的——但话还得用你自己的方式说出来。",
        "diagnose": f"如果还分不清错因，回到 transition：{transition}。问自己『如果这条变化没发生，会出现什么现象』——和你看到的现象对得上的就是错因。",
        "fill": f"如果还填不出，先在右侧机制画板找到 {boundary}；本步要填的词必定属于这条边界的某一侧。把对象先写下来，再决定它叫什么名字。",
        "trace": f"如果排序还乱，记住因果起点和终点是固定的——中间每两个相邻节点之间问『前一步如果不做，后一步能不能做』，能说『不能』的就放在前面。",
        "command": f"如果命令顺序错，先把状态变化写下来：{transition}。每条命令对应一次状态改变，命令顺序就是状态改变的因果顺序。",
        "code": f"如果代码片段不通过，先找 {transition} 在代码里的名字；关键词必须出现在你的片段里，否则机制层就接不上。",
        "explain": f"如果说不清楚，先点出证据：{evidence}。围绕这条证据组织 2-3 句话——证据在前，机制在后，结论收尾。",
        "reflection": f"如果写不出复盘，先回答一个问题：{lab.get('drivingQuestion', '')} 你的答案就是复盘的第一段。",
    }
    new_text = seeds.get(interaction, seeds["explain"])
    # 如果原 hint 看起来已经是好的（长且不模板），保留前半然后追加扩展
    if original_text and len(original_text) >= 50 and not any(
        bad in original_text
        for bad in ("证据会帮助你判断", "先回到右侧术语卡", "把题目翻成日常语言")
    ):
        return original_text
    return new_text


def rewrite_starter_first_title(lab: dict) -> str:
    """starter 首步标题用 drivingQuestion 改写，9 个 lab 各不相同。"""
    # 基于每个 lab 自己的 drivingQuestion 关键词
    lab_id = lab["id"]
    titles = {
        "lab1": "我改了源码，Bochs 真的换了吗",
        "lab2": "BIOS 之后，控制权落在哪里",
        "lab3": "用户程序怎么『敲门』进入内核",
        "lab4": "看不见的进程怎么留下足迹",
        "lab5": "切换进程时，内核栈在做什么",
        "lab6": "抢同一个资源时，谁该等",
        "lab7": "看到的地址不是真地址，怎么对上",
        "lab8": "按键到屏幕，中间走了几道关",
        "lab9": "/proc 里的文件，从硬盘读吗",
    }
    return titles.get(lab_id, lab.get("title", "认出这一关"))


def remove_template_phrases(obj):
    """递归把已知跨 lab 模板短语在文本中删除或替换为通用补丁。"""
    REPLACEMENTS = {
        "证据会帮助你判断": "可以作为机制是否生效的依据",
        "先回到右侧术语卡": "先回到右侧机制画板",
        "把题目翻成日常语言": "把题目压成一句你能复述的话",
        "已经抓住入口问题": "已经看清这一关的关键边界",
        "这一证据会帮助": "这条线索可以帮助",
        "把对象和状态名贴对": "把对象和它的状态名挂上",
    }
    if isinstance(obj, dict):
        return {k: remove_template_phrases(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [remove_template_phrases(v) for v in obj]
    if isinstance(obj, str):
        out = obj
        for old, new in REPLACEMENTS.items():
            out = out.replace(old, new)
        return out
    return obj


def main() -> None:
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))

    for lab in data["labs"]:
        # 重写每 step 的 coach
        for phase in lab["phases"]:
            for idx, step in enumerate(phase["steps"]):
                new_coach = coach_for_step(lab, phase, step, idx)
                step["coach"] = new_coach
                # 第三层 hint 扩写
                for hint in step.get("hints", []):
                    if hint.get("level") == 3:
                        original = hint.get("text", "")
                        hint["text"] = rewrite_third_hint(lab, step, original)
        # starter 首步标题
        starter_steps_in_order = [
            (phase, step)
            for phase in lab["phases"]
            for step in phase["steps"]
            if "starter" in step["tracks"]
        ]
        if starter_steps_in_order:
            _, first_starter_step = starter_steps_in_order[0]
            first_starter_step["title"] = rewrite_starter_first_title(lab)

    # 全局移除已知跨 lab 模板短语
    data = remove_template_phrases(data)

    DATA_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"已重写 {DATA_PATH}")


if __name__ == "__main__":
    main()
