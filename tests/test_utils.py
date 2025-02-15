from superfork.utils import (
    create_repo_replace_function,
    create_source_function,
    replace_at_mentions,
    replace_references,
    text_pipeline,
)


def test_multiple_functions():
    def to_uppercase(text: str) -> str:
        return text.upper()

    def to_reverse(text: str) -> str:
        return text[::-1]

    text = "Hello @user!"
    expected = "HELLO @USER!"
    fns = [to_reverse, to_uppercase, to_reverse]
    result = text_pipeline(text, fns)
    assert result == expected


def test_replace_references():
    text = "This is a foo example."
    ref_a = r"foo"
    ref_b = r"bar"
    replacer = replace_references(ref_a, ref_b)
    expected = "This is a bar example."
    result = replacer(text)
    assert result == expected


def test_replace_repo_reference():
    text = "This is a foo/bar and a ffffoo.barrrr example."
    ref_a = r"\bfoo/bar\b"
    ref_b = r"bar/baz"
    replacer = replace_references(ref_a, ref_b)
    expected = "This is a bar/baz and a ffffoo.barrrr example."
    result = replacer(text)
    assert result == expected


def test_replace_at_mentions():
    text = "Hello @user!"
    expected = "Hello `@user`!"
    result = replace_at_mentions(text)
    assert result == expected


def test_replace_at_mentions_multiple():
    text = "Hello @user1 and @user2!"
    expected = "Hello `@user1` and `@user2`!"
    result = replace_at_mentions(text)
    assert result == expected


def test_create_repo_replace():
    repo_1 = "foo/bar"
    repo_2 = "bar/baz"
    text = "This is a foo/bar and a ffffoo.barrrr example."
    expected = "This is a bar/baz and a ffffoo.barrrr example."
    result = create_repo_replace_function(repo_1, repo_2)(text)
    assert result == expected


def test_create_source():
    text = "Hello world!"
    source = "test_user"
    datestring = "2023-10-01"
    url = "https://github.com/test_user/test_repo/issues/1"
    expected = "Hello world!\n\n<sub>Source: [`test_user`](https://github.com/test_user) on [2023-10-01](https://github.com/test_user/test_repo/issues/1).</sub>"
    result = create_source_function(text, source, datestring, url)(text)
    assert result == expected
