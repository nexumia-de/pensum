"""Find tasks by words in their title or notes, open ones first, then the
archive. No GTK."""


def _matches(task, words):
    text = f"{task.get('title') or ''}\n{task.get('notes') or ''}".casefold()
    return all(word in text for word in words)


def search(ds, query, limit=100):
    """[(task, archived)] for every task containing all words of `query`."""
    words = query.casefold().split()
    if not words:
        return []
    found = [(t, False) for t in ds.tasks.values() if _matches(t, words)]
    found.sort(key=lambda item: (bool(item[0].get("isDone")),
                                 -(item[0].get("modified") or item[0].get("created") or 0)))
    for archive in ("archiveYoung", "archiveOld"):
        entities = ds.data[archive]["task"]["entities"]
        hits = [(t, True) for t in entities.values() if _matches(t, words)]
        hits.sort(key=lambda item: -(item[0].get("doneOn") or 0))
        found += hits
    return found[:limit]
