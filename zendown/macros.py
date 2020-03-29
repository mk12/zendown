"""Built-in macros available in all Zendown projects."""


from mistletoe.block_token import Paragraph


def defs(ctx, arg, children):
    items = []
    for child in children:
        if child.__class__.__name__ == "Heading" and child.level == 1:
            items.append({"term": child, "children": []})
        else:
            items[-1]["children"].append(child)
    paragraphs = []
    for item in items:
        term = ctx.render(item["term"].children)
        para = ctx.render(item["children"][0].children)
        first = Paragraph([f"**{term}**: {para}"])
        paragraphs.append(first)
        paragraphs.extend(item["children"][1:])
    return "\n".join(ctx.render(p) for p in paragraphs)


def note(ctx, arg, children):
    return f'<div class="note">\n{ctx.render(children)}\n</div>'
