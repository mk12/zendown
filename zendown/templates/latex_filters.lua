function Div(el)
    if el.classes[1] == "hs-callout-type-note" then
        -- insert element in front
        table.insert(
        el.content, 1,
        pandoc.RawBlock("latex", "\\begin{Note}"))
        -- insert element at the back
        table.insert(
        el.content,
        pandoc.RawBlock("latex", "\\end{Note}"))
    elseif el.classes[1] == "hs-callout-type-tip" then
        -- insert element in front
        table.insert(
        el.content, 1,
        pandoc.RawBlock("latex", "\\begin{Tip}"))
        -- insert element at the back
        table.insert(
        el.content,
        pandoc.RawBlock("latex", "\\end{Tip}"))
    elseif el.classes[1] == "hs-callout-type-caution" then
        -- insert element in front
        table.insert(
        el.content, 1,
        pandoc.RawBlock("latex", "\\begin{Caution}"))
        -- insert element at the back
        table.insert(
        el.content,
        pandoc.RawBlock("latex", "\\end{Caution}"))
    elseif el.classes[1] == "hs-callout-type-warning" then
        -- insert element in front
        table.insert(
        el.content, 1,
        pandoc.RawBlock("latex", "\\begin{Warning}"))
        -- insert element at the back
        table.insert(
        el.content,
        pandoc.RawBlock("latex", "\\end{Warning}"))
    end
    return el
end
