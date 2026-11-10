import pytest

from app.application.chat.effort import effort_for


@pytest.mark.parametrize(
    "text",
    [
        "Interprete para mim o capítulo 1 de João.",
        "Interprete João 1",
        "Estude comigo o Salmo 23",
        "Explique Romanos 8",
        "Me ajude a entender Lucas 15",
        "Faça um estudo de 1 Coríntios 13",
        "explica o capítulo 53 de Isaías",
    ],
)
def test_chapter_study_gets_study_effort(text: str) -> None:
    assert effort_for(text, "high") == "high"


@pytest.mark.parametrize(
    "text",
    [
        "Estou com medo de não conseguir pagar as contas",
        "Explique João 3:16",
        "O que é graça?",
        "✨ Uma palavra pra mim",
    ],
)
def test_other_requests_keep_default(text: str) -> None:
    assert effort_for(text, "high") is None


def test_disabled_study_effort() -> None:
    assert effort_for("Interprete João 1", None) is None


@pytest.mark.parametrize(
    "text",
    [
        "Na sua opinião, o crente pode perder a salvação?",
        "O que você acha sobre o dízimo hoje?",
        "Qual a sua opinião sobre tatuagem?",
        "o que vc acha disso?",
        "Qual é a sua interpretação de Gênesis 1?",
        "Na sua visão, o Apocalipse já se cumpriu?",
        "Você acredita que Jó existiu de verdade?",
        "O que você pensa sobre isso?",
    ],
)
def test_detects_opinion_requests(text: str) -> None:
    from app.application.chat.effort import asks_opinion

    assert asks_opinion(text)
    assert effort_for(text, "high") == "high"


@pytest.mark.parametrize(
    "text",
    [
        "O que a Bíblia diz sobre o dízimo?",
        "Acho que estou com medo do futuro",
        "Explique João 3:16",
        "Interprete o Salmo 23:1",
    ],
)
def test_other_texts_are_not_opinion_requests(text: str) -> None:
    from app.application.chat.effort import asks_opinion

    assert not asks_opinion(text)


@pytest.mark.parametrize(
    "text",
    [
        "Me envie um breve resumo de Romanos 8",
        "Explique brevemente o que é graça",
        "Resuma o livro de Rute",
        "Qual o resumo de Gênesis 1?",
        "Responda de forma sucinta: o que é fé?",
        "Em poucas palavras, quem foi Davi?",
        "Seja breve: o que é justificação?",
        "me dá uma resposta curta sobre o batismo",
        "resumidamente, o que acontece em Atos 2?",
    ],
)
def test_detects_brief_requests(text: str) -> None:
    from app.application.chat.effort import wants_brief

    assert wants_brief(text)


@pytest.mark.parametrize(
    "text",
    [
        "Jesus volta em breve?",
        "Interprete João 1",
        "Estou com medo de não conseguir pagar as contas",
        "A vida é curta, o que a Bíblia diz?",
    ],
)
def test_other_texts_are_not_brief_requests(text: str) -> None:
    from app.application.chat.effort import wants_brief

    assert not wants_brief(text)


def test_brief_request_keeps_default_effort() -> None:
    assert effort_for("Resuma João 1 brevemente", "high") is None
    assert effort_for("Na sua opinião, em poucas palavras, o que é fé?", "high") is None


@pytest.mark.parametrize(
    "text",
    [
        "Crie para mim um plano de estudo sobre a aliança com Abraão",
        "Quero um plano de estudos sobre o Espírito Santo",
        "monta um roteiro de estudo sobre Daniel",
    ],
)
def test_detects_study_plan_requests(text: str) -> None:
    from app.application.chat.effort import wants_plan

    assert wants_plan(text)


@pytest.mark.parametrize(
    "text", ["Me dá um plano de leitura da Bíblia", "Como planejar meu devocional?", "Interprete João 1"]
)
def test_other_texts_are_not_study_plan_requests(text: str) -> None:
    from app.application.chat.effort import wants_plan

    assert not wants_plan(text)


def test_wants_complex_only_when_message_starts_with_the_word() -> None:
    from app.application.chat.effort import wants_complex

    assert wants_complex("Complexo: a aliança com Abraão")
    assert wants_complex("  complexo o que é a graça?")
    assert wants_complex("COMPLEXO - Romanos 9")
    assert not wants_complex("Esse tema é complexo demais")
    assert not wants_complex("Complexidade da Trindade")


def test_wants_thinkers_on_philosophy_and_skeptic_topics() -> None:
    from app.application.chat.effort import wants_thinkers

    assert wants_thinkers("Se Deus é bom, por que existe o mal?")
    assert wants_thinkers("O que os filósofos dizem sobre fé e razão?")
    assert wants_thinkers("Como responder a um ateu que diz que Deus não existe?")
    assert wants_thinkers("Nietzsche disse que Deus está morto")
    assert not wants_thinkers("O que significa graça na Bíblia?")
    assert not wants_thinkers("Me explique João 3")
