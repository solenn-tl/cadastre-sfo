-- Per-slide incremental lists.
-- Usage:  ## Slide title {.incremental}      -> lists on this slide appear one by one
--         ## Slide title {.nonincremental}   -> lists on this slide appear all at once
-- Slides without a class follow the global `incremental:` option in main.qmd.
-- An explicit ::: {.incremental} / ::: {.nonincremental} div inside a slide still wins.

local MODES = { incremental = true, nonincremental = true }

local function mode_of(attr)
  for _, c in ipairs(attr.classes) do
    if MODES[c] then return c end
  end
end

local function wrap_lists(block, mode)
  local filter = {
    traverse = "topdown",
    Div = function(div)
      -- keep explicit per-list choices untouched
      if mode_of(div.attr) then return div, false end
    end,
    BulletList = function(l)
      return pandoc.Div({ l }, pandoc.Attr("", { mode })), false
    end,
    OrderedList = function(l)
      return pandoc.Div({ l }, pandoc.Attr("", { mode })), false
    end,
  }
  return pandoc.walk_block(pandoc.Div({ block }), filter).content[1]
end

function Pandoc(doc)
  local mode = nil
  for i, block in ipairs(doc.blocks) do
    if block.t == "Header" and block.level <= 2 then
      mode = mode_of(block.attr)
      if mode then
        -- remove the class from the header so it doesn't leak into the HTML
        block.attr.classes = block.attr.classes:filter(function(c) return not MODES[c] end)
      end
    elseif mode then
      doc.blocks[i] = wrap_lists(block, mode)
    end
  end
  return doc
end
