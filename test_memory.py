from memories_manager import UserMemory


def test_add_update_remove_fact(tmp_path):
    memory = UserMemory(memory_root=tmp_path)

    key = memory.add_fact("123", "favorite color: green", first_name="Ada")
    assert key == "Favorite Color"

    memory.add_fact("123", "Favorite Color: blue", first_name="Ada")
    data = memory.load_memory("123")
    assert data["facts"] == {"Favorite Color": "blue"}

    removed = memory.remove_fact("123", "favorite color")
    assert removed == "Favorite Color"
    assert memory.load_memory("123")["facts"] == {}


def test_extract_facts_from_message():
    memory = UserMemory()

    assert memory.extract_facts_from_message("Remember that I prefer tea.") == [
        "I prefer tea"
    ]
    assert memory.extract_facts_from_message("nothing to save") == []


def test_save_conversation_and_stats(tmp_path):
    memory = UserMemory(memory_root=tmp_path)

    memory.save_conversation("abc", "User", "hello", first_name="Sam")
    memory.save_conversation("abc", "Bot", "hi")

    stats = memory.get_stats("abc")
    assert stats["display_name"] == "Sam"
    assert stats["conversation_count"] == 2
    assert stats["memory_size"] > 0


def test_retrieve_relevant_facts_with_lexical_fallback(tmp_path):
    memory = UserMemory(memory_root=tmp_path)
    memory._embedding_available = False

    memory.add_fact("123", "favorite editor: VS Code")
    memory.add_fact("123", "favorite food: dosa")

    facts = memory.retrieve_relevant_facts("123", "which editor should I use?", top_k=1)

    assert facts[0]["key"] == "Favorite Editor"


def test_clear_memory(tmp_path):
    memory = UserMemory(memory_root=tmp_path)
    memory.add_fact("123", "timezone: IST")

    memory.clear_memory("123")

    assert not (tmp_path / "123").exists()

