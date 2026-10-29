import sqlite3
import pytest
from produto_repository import ProdutoRepository
from estoque_service import EstoqueService, EstoqueInsuficienteError

@pytest.fixture
def conexao():
    conn = sqlite3.connect(":memory:")

    conn.execute("""
        CREATE TABLE produtos (
            id INTEGER PRIMARY KEY,
            nome VARCHAR(100) NOT NULL,
            quantidade INT NOT NULL
        );
    """)

    conn.execute("INSERT INTO produtos (id, nome, quantidade) VALUES (1, 'Teclado', 10)")
    conn.commit()
    yield conn
    conn.close()


def test_adicionar_estoque_atualiza_banco(conexao):
    # Arrange
    repo = ProdutoRepository(conexao)
    service = EstoqueService(repo)

    # Act
    service.adicionar_estoque(1, 5)

    # Assert
    cursor = conexao.execute("SELECT quantidade FROM produtos WHERE id = 1")
    qtd_no_banco = cursor.fetchone()[0]
    assert qtd_no_banco == 15


def test_vender_produto_com_estoque_suficiente(conexao):
    # Arrange
    repo = ProdutoRepository(conexao)
    service = EstoqueService(repo)

    # Act
    service.vender_produto(1, 4)

    # Assert
    cursor = conexao.execute("SELECT quantidade FROM produtos WHERE id = 1")
    qtd_no_banco = cursor.fetchone()[0]
    assert qtd_no_banco == 6


def test_vender_produto_com_estoque_insuficiente_nao_altera_banco(conexao):
    # Arrange
    repo = ProdutoRepository(conexao)
    service = EstoqueService(repo)

    # Act e Assert
    with pytest.raises(EstoqueInsuficienteError):
        service.vender_produto(1, 20)

    #Assert
    cursor = conexao.execute("SELECT quantidade FROM produtos WHERE id = 1")
    qtd_no_banco = cursor.fetchone()[0]
    assert qtd_no_banco == 10


@pytest.mark.parametrize("qtd_invalida", [11, 15, 100])
def test_vender_quantidades_maiores_que_estoque_falha_e_nao_altera_banco(conexao, qtd_invalida):
    #Arrange
    repo = ProdutoRepository(conexao)
    service = EstoqueService(repo)

    #Act e Assert
    with pytest.raises(EstoqueInsuficienteError):
        service.vender_produto(1, qtd_invalida)

    #Assert
    cursor = conexao.execute("SELECT quantidade FROM produtos WHERE id = 1")
    qtd_no_banco = cursor.fetchone()[0]
    assert qtd_no_banco == 10
