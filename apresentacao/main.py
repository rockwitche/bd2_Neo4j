"""
Instalar: pip install -r requirements.txt
na outra maquina trocar a URL por: bolt://100.122.141.42:7687
no host: bolt://localhost:7687
"""
import os
import random
import time
from datetime import date

from neo4j import GraphDatabase

URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
USER = os.getenv("NEO4J_USER", "neo4j")
PASSWORD = os.getenv("NEO4J_PASSWORD", "Jupiter07?")

driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))


def run(query, **params):
    with driver.session() as session:
        return list(session.run(query, **params))


def usuario_existe(email):
    return bool(run("MATCH (u:Usuario {email: $email}) RETURN u", email=email))


def filme_existe(titulo):
    return bool(run("MATCH (f:Filme {titulo: $titulo}) RETURN f", titulo=titulo))


def ja_avaliou(email, titulo):
    return bool(
        run(
            """
            MATCH (:Usuario {email: $email})-[r:AVALIOU]->(:Filme {titulo: $titulo})
            RETURN r
            """,
            email=email, titulo=titulo,
        )
    )


def cadastrar_usuario(email, nome):
    if usuario_existe(email):
        return False
    run("CREATE (:Usuario {email: $email, nome: $nome})", email=email, nome=nome)
    return True


def avaliar(email, titulo, nota):
    if not usuario_existe(email):
        return "sem_usuario"
    if not filme_existe(titulo):
        return "sem_filme"
    if ja_avaliou(email, titulo):
        return "ja_avaliado"
    run(
        """
        MATCH (u:Usuario {email: $email}), (f:Filme {titulo: $titulo})
        CREATE (u)-[:AVALIOU {nota: $nota, data: date($data)}]->(f)
        """,
        email=email, titulo=titulo, nota=nota, data=str(date.today()),
    )
    return "ok"


def minhas_avaliacoes(email):
    return run(
        """
        MATCH (:Usuario {email: $email})-[r:AVALIOU]->(f:Filme)
        RETURN f.titulo AS titulo, r.nota AS nota ORDER BY r.nota DESC
        """,
        email=email,
    )


def media_filme(titulo):
    r = run(
        """
        MATCH (:Usuario)-[a:AVALIOU]->(f:Filme {titulo: $titulo})
        RETURN count(a) AS total, round(avg(a.nota), 2) AS media
        """,
        titulo=titulo,
    )
    return r[0]["total"], r[0]["media"]


def top_filmes(n=10):
    return run(
        """
        MATCH (:Usuario)-[a:AVALIOU]->(f:Filme)
        WITH f, count(a) AS total, avg(a.nota) AS media
        WHERE total > 100
        RETURN f.titulo AS titulo, total, round(media, 2) AS media
        ORDER BY media DESC LIMIT $n
        """,
        n=n,
    )


def usuario_compativel(email, minimo=2):
    r = run(
        """
        MATCH (u:Usuario {email: $email})-[a:AVALIOU]->(f:Filme)<-[b:AVALIOU]-(o:Usuario)
        WHERE o <> u
        WITH o, count(f) AS em_comum, avg(abs(a.nota - b.nota)) AS dif
        WHERE em_comum >= $minimo
        RETURN o.nome AS nome, o.email AS email, em_comum, round(dif, 2) AS dif
        ORDER BY dif ASC, em_comum DESC LIMIT 1
        """,
        email=email, minimo=minimo,
    )
    return r[0] if r else None


def simulador(qtd=300, intervalo=0.05):
    filmes = [r["titulo"] for r in run("MATCH (f:Filme) RETURN f.titulo AS titulo")]
    criadas = 0
    while criadas < qtd:
        email = f"usuario{random.randint(1, 100000)}@exemplo.com"
        titulo = random.choice(filmes)
        nota = random.randint(1, 5)
        if avaliar(email, titulo, nota) != "ok":
            continue
        criadas += 1
        total = run("MATCH ()-[r:AVALIOU]->() RETURN count(r) AS c")[0]["c"]
        print(f"[{criadas}/{qtd}] {email} deu {nota} para '{titulo}' | total de avaliações: {total}")
        time.sleep(intervalo)


MENSAGENS = {
    "ok": "Avaliação salva.",
    "sem_usuario": "Usuário não cadastrado. Use a opção 1 primeiro.",
    "sem_filme": "Filme não encontrado. Confira o título exato.",
    "ja_avaliado": "Esse usuário já avaliou esse filme.",
}

MENU = """
1) Cadastrar usuário
2) Avaliar um filme
3) Minhas avaliações
4) Achar usuário mais compatível
5) Média de um filme
6) Top 10 filmes
7) Simulador em tempo real
0) Sair
> """

if __name__ == "__main__":
    while True:
        op = input(MENU).strip()
        if op == "1":
            email = input("email: ").strip()
            nome = input("nome: ").strip()
            if cadastrar_usuario(email, nome):
                print("Usuário cadastrado.")
            else:
                print("Esse e-mail já está cadastrado.")
        elif op == "2":
            email = input("email: ").strip()
            titulo = input("filme (título exato): ").strip()
            try:
                nota = int(input("nota (1-5): "))
            except ValueError:
                print("Nota inválida.")
                continue
            if not 1 <= nota <= 5:
                print("A nota deve ser de 1 a 5.")
                continue
            print(MENSAGENS[avaliar(email, titulo, nota)])
        elif op == "3":
            for r in minhas_avaliacoes(input("email: ").strip()):
                print(f"{r['titulo']}: {r['nota']}")
        elif op == "4":
            r = usuario_compativel(input("seu email: ").strip())
            if r:
                print(f"Mais compatível: {r['nome']} ({r['email']})")
                print(f"{r['em_comum']} filmes em comum, diferença média de nota: {r['dif']}")
            else:
                print("Nenhum usuário compatível encontrado.")
        elif op == "5":
            total, media = media_filme(input("filme: ").strip())
            print(f"{total} avaliações, média {media}")
        elif op == "6":
            for r in top_filmes():
                print(f"{r['titulo']}: {r['media']} ({r['total']} avaliações)")
        elif op == "7":
            simulador()
        elif op == "0":
            break
    driver.close()