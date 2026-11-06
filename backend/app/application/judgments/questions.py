from app.application.judgments.ports import ChoiceQ, NoulQ, ScoreQ

TRIAGE = {
    "crise": NoulQ(
        "A `mensagem` indica risco à vida da pessoa: ideação suicida, desejo de morrer, de 'sumir' ou de deixar de "
        "existir, ou intenção de se ferir?"
    ),
    "momento": ChoiceQ(
        "Qual é o principal momento que a pessoa vive ou o principal pedido na `mensagem`?",
        {
            "financas": "aperto, medo ou decisão sobre dinheiro, dívidas, contas, trabalho ou provisão",
            "pecado_arrependimento": "culpa, queda, pecado, sente que se afastou do que Jesus ensinou",
            "estudo": "quer aprender ou estudar um tema, um livro, uma passagem ou uma palavra da Bíblia",
            "palavra": "pede uma palavra, um versículo, consolo ou encorajamento para o dia",
            "outro": "nenhum dos anteriores (saudação, dúvida geral, outro assunto)",
        },
    ),
    "angustia": ScoreQ(
        "Quão intensa é a angústia emocional expressa na `mensagem`?",
        [
            "tranquila: nenhuma angústia aparente",
            "alguma preocupação: incômodo ou dúvida, mas sob controle",
            "angústia forte: medo, culpa ou tristeza intensos",
            "desespero: sente que não aguenta mais ou que não há saída",
        ],
    ),
}

GUARD = {
    "prosperidade": NoulQ(
        "A `resposta` promete bênção material ou financeira (dinheiro, riqueza, cura de dívidas) em troca de fé, "
        "oferta, dízimo ou 'semeadura'?"
    ),
    "investimento": NoulQ(
        "A `resposta` recomenda comprar, vender ou investir em um ativo, produto financeiro ou investimento "
        "específico (ação, fundo, criptomoeda, título nomeado)?"
    ),
    "condenacao": NoulQ(
        "A `resposta` humilha, condena ou envergonha a pessoa, em vez de chamar ao arrependimento com verdade e graça?"
    ),
}
GUARD_KINDS = {
    "prosperidade": "teologia_prosperidade",
    "investimento": "teologia_investimento",
    "condenacao": "teologia_condenacao",
}

FIDELITY = {
    "relacao": ChoiceQ(
        "Como a `afirmacao` (escrita por um assistente logo depois de citar o versículo) se relaciona com o "
        "texto do `versiculo`?",
        {
            "apoia": "a afirmação expressa, aplica ou deriva razoavelmente o que o versículo diz",
            "contradiz": "a afirmação atribui ao versículo algo oposto ao que ele diz ou promete algo que ele não "
            "promete",
            "nao_trata": "a afirmação fala de outra coisa; o versículo não trata disso",
        },
    )
}

SENSITIVE = {
    "sensivel": NoulQ(
        "O `conteudo` contém um dado sensível: CPF, RG, senha, PIN, número de cartão, número de conta bancária "
        "ou chave Pix?"
    )
}

FACT = {
    "tipo": ChoiceQ(
        "Que tipo de afirmação conferível a `frase` (escrita por um assistente bíblico) faz?",
        {
            "parentesco": "afirma o parentesco entre duas pessoas bíblicas (pai, mãe, avô, avó, bisavô, bisavó, filho, "
            "filha, neto, neta, bisneto, marido, esposa)",
            "ocorrencias": "afirma quantas vezes ou em quantos lugares uma palavra hebraica ou grega aparece "
            "na Bíblia, "
            "inclusive que ela só aparece ali",
            "outra": "nenhuma das anteriores (opinião, interpretação, aplicação, história, outro fato)",
        },
    ),
    "parentesco": ChoiceQ(
        "Segundo a `frase`, o que `pessoa_a` é de `pessoa_b`?",
        {
            "pai_ou_mae": "pai ou mãe",
            "avo": "avô ou avó",
            "bisavo": "bisavô ou bisavó",
            "filho": "filho ou filha",
            "neto": "neto ou neta",
            "bisneto": "bisneto ou bisneta",
            "conjuge": "marido ou esposa",
            "nenhum": "a frase não afirma parentesco entre as duas",
        },
    ),
    "ocorrencias": ChoiceQ(
        "Sobre a palavra do original citada na `frase`, o que ela afirma?",
        {
            "unica": "que a palavra aparece uma única vez, só naquele lugar",
            "numero": "um número exato de vezes ou de lugares em que a palavra aparece",
            "nao_afirma": "não afirma quantidade",
        },
    ),
}
