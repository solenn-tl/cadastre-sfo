-- Remplace imgs/... par imgs_web/... (copies allégées créées par optimize_images.py)
-- dans les images Markdown, les balises <img> HTML et les images de fond.
-- Si la copie allégée n'existe pas, le chemin original est conservé.

local function exists(path)
  local f = io.open(path, "rb")
  if f then f:close() return true end
  return false
end

local function web(path)
  local alt = path:gsub("^imgs/", "imgs_web/", 1)
  if alt ~= path and exists(alt) then return alt end
  return path
end

local function rewrite_html(text)
  return (text:gsub('(src=")(imgs/[^"]+)(")', function(a, p, b)
    return a .. web(p) .. b
  end))
end

local function rewrite_attr(el)
  for k, v in pairs(el.attributes) do
    if k:match("background%-image$") then el.attributes[k] = web(v) end
  end
  return el
end

return {
  {
    Meta = function(meta)
      local tsa = meta["title-slide-attributes"]
      if tsa and tsa["data-background-image"] then
        local v = pandoc.utils.stringify(tsa["data-background-image"])
        tsa["data-background-image"] = pandoc.MetaString(web(v))
      end
      return meta
    end,
    Image = function(img) img.src = web(img.src) return img end,
    RawBlock = function(raw)
      if raw.format:match("html") then raw.text = rewrite_html(raw.text) end
      return raw
    end,
    RawInline = function(raw)
      if raw.format:match("html") then raw.text = rewrite_html(raw.text) end
      return raw
    end,
    Header = rewrite_attr,
    Div = rewrite_attr,
  },
}
