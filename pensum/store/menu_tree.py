"""Folders of the menu as Super Productivity keeps them: `menuTree`'s
`projectTree` and `tagTree` hold folder nodes `{k: "f", id, name,
isExpanded, children}` beside project (`k: "p"`) and tag (`k: "t"`)
nodes (read at commit 9980fd76: `menu-tree.model.ts`,
`menu-tree.reducer.ts`, `menu-tree.service.ts`).

- A new folder has a random UUID, the trimmed name (an empty name adds
  nothing), `isExpanded: true` and no children; it goes to the end of
  the tree or of its parent folder.
- Moving a list into a folder removes its node wherever it was and
  appends it to the folder, which opens; without a folder (or when the
  folder is gone) it goes to the end of the tree.
- Renaming changes `name`; deleting removes the folder node with its
  children, as Super Productivity's reducer does: the lists in it are
  shown after the tree (`Dataset._tree_order`) and stay in the data.
- A folder without `isExpanded` counts as open.
No GTK."""
import uuid

TREES = {"project": ("projectTree", "p"), "tag": ("tagTree", "t")}


def _tree(ds, kind):
    return ds.data.setdefault("menuTree", {}).setdefault(TREES[kind][0], [])


def _find(nodes, folder_id):
    for node in nodes:
        if node.get("k") == "f":
            if node.get("id") == folder_id:
                return node
            found = _find(node.get("children") or [], folder_id)
            if found:
                return found
    return None


def _remove_item(nodes, item_id, letter):
    kept = []
    for node in nodes:
        if node.get("k") == letter and node.get("id") == item_id:
            continue
        if node.get("k") == "f":
            node["children"] = _remove_item(node.get("children") or [], item_id, letter)
        kept.append(node)
    return kept


def entries(ds, kind, ids):
    """The menu in tree order: ("folder", node, depth) and ("item", id,
    depth) for lists among `ids`; lists the tree misses follow at depth 0.
    The children of a closed folder are left out."""
    letter = TREES[kind][1]
    found, seen = [], set()

    def walk(nodes, depth, shown):
        for node in nodes or ():
            if node.get("k") == "f":
                if shown:
                    found.append(("folder", node, depth))
                walk(node.get("children"), depth + 1,
                     shown and node.get("isExpanded", True) is not False)
            elif node.get("k") == letter and node.get("id") in ids and node["id"] not in seen:
                seen.add(node["id"])
                if shown:
                    found.append(("item", node["id"], depth))

    walk(_tree(ds, kind), 0, True)
    found += [("item", i, 0) for i in ids if i not in seen]
    return found


def folders(ds, kind):
    """(id, name, depth) of every folder, for a "Move to Folder" menu."""
    found = []

    def walk(nodes, depth):
        for node in nodes or ():
            if node.get("k") == "f":
                found.append((node["id"], node.get("name", ""), depth))
                walk(node.get("children"), depth + 1)

    walk(_tree(ds, kind), 0)
    return found


def folder_of(ds, kind, item_id):
    letter = TREES[kind][1]

    def walk(nodes, parent):
        for node in nodes or ():
            if node.get("k") == letter and node.get("id") == item_id:
                return parent
            if node.get("k") == "f":
                hit = walk(node.get("children"), node["id"])
                if hit is not False:
                    return hit
        return False

    hit = walk(_tree(ds, kind), None)
    return None if hit is False else hit


def add_folder(ds, kind, name, parent_id=None):
    name = (name or "").strip()
    if not name:
        return None
    folder = {"k": "f", "id": str(uuid.uuid4()), "name": name, "isExpanded": True,
              "children": []}
    _insert(ds, kind, folder, parent_id)
    return folder


def _insert(ds, kind, node, parent_id):
    tree = _tree(ds, kind)
    target = _find(tree, parent_id) if parent_id else None
    if target is None:
        tree.append(node)
    else:
        target.setdefault("children", []).append(node)
        target["isExpanded"] = True


def move_to_folder(ds, kind, item_id, folder_id):
    letter = TREES[kind][1]
    tree_name = TREES[kind][0]
    ds.data["menuTree"][tree_name] = _remove_item(_tree(ds, kind), item_id, letter)
    _insert(ds, kind, {"k": letter, "id": item_id}, folder_id)


def rename_folder(ds, kind, folder_id, name):
    folder = _find(_tree(ds, kind), folder_id)
    name = (name or "").strip()
    if folder is None or not name:
        return False
    folder["name"] = name
    return True


def set_expanded(ds, kind, folder_id, value):
    folder = _find(_tree(ds, kind), folder_id)
    if folder is None:
        return False
    folder["isExpanded"] = bool(value)
    return True


def delete_folder(ds, kind, folder_id):
    tree_name = TREES[kind][0]

    def drop(nodes):
        return [dict(n, children=drop(n.get("children") or [])) if n.get("k") == "f" else n
                for n in nodes if not (n.get("k") == "f" and n.get("id") == folder_id)]

    before = _tree(ds, kind)
    ds.data["menuTree"][tree_name] = drop(before)
    return ds.data["menuTree"][tree_name] != before
