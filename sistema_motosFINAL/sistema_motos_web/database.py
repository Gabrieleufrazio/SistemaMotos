import mysql.connector
import os
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from config import MYSQL_CONFIG

# Helper function to get database connection
def get_db_connection():
    return mysql.connector.connect(**MYSQL_CONFIG)

# Helpers de formatação seguros
def br_moeda_safe(valor):
    try:
        if valor is None:
            valor = 0
        return f"R$ {float(valor):,.2f}".replace(",", "v").replace(".", ",").replace("v", ".")
    except Exception:
        return "R$ 0,00"

def br_km_safe(valor):
    try:
        if valor is None:
            valor = 0
        return f"{int(float(valor)):,.0f}".replace(",", ".")
    except Exception:
        return "0"
def migrar_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Verificar se a coluna 'email' existe em 'usuarios'
        cursor.execute("SHOW COLUMNS FROM usuarios LIKE 'email'")
        if not cursor.fetchone():
            print("Aplicando migração: Adicionando coluna 'email' à tabela 'usuarios'.")
            cursor.execute("ALTER TABLE usuarios ADD COLUMN email VARCHAR(255)")
            conn.commit()

        # Verificar e adicionar colunas ausentes na tabela 'motos'
        cursor.execute("SHOW COLUMNS FROM motos")
        colunas_motos = [col[0] for col in cursor.fetchall()]
        colunas_necessarias = [
            ("renavam", "VARCHAR(255)"),
            ("doc_moto", "VARCHAR(255)"),
            ("documento_fornecedor", "VARCHAR(255)"),
            ("comprovante_residencia", "VARCHAR(255)"),
            ("data_cadastro", "DATE"),
            ("hora_cadastro", "TIME"),
            ("nome_cliente", "VARCHAR(255)"),
            ("cpf_cliente", "VARCHAR(255)"),
            ("rua_cliente", "TEXT"),
            ("cep_cliente", "VARCHAR(255)"),
            ("celular_cliente", "VARCHAR(255)"),
            ("referencia", "VARCHAR(255)"),
            ("celular_referencia", "VARCHAR(255)"),
            ("debitos", "TEXT"),
            ("observacoes", "TEXT"),
            ("chassi", "VARCHAR(255)"),
        ]
        for nome_coluna, tipo_coluna in colunas_necessarias:
            if nome_coluna not in colunas_motos:
                print(f"Aplicando migração: Adicionando coluna '{nome_coluna}' à tabela 'motos'.")
                cursor.execute(f"ALTER TABLE motos ADD COLUMN {nome_coluna} {tipo_coluna}")
                conn.commit()

        # Renomear coluna antiga 'laudo' para 'documento_fornecedor' se existir e a nova não existir
        if 'laudo' in colunas_motos and 'documento_fornecedor' not in colunas_motos:
            try:
                print("Aplicando migração: Renomeando coluna 'laudo' para 'documento_fornecedor' em 'motos'.")
                cursor.execute("ALTER TABLE motos CHANGE COLUMN laudo documento_fornecedor VARCHAR(255)")
                conn.commit()
            except Exception as e:
                print(f"Falha ao renomear coluna laudo->documento_fornecedor: {e}")

        # Verificar existência da tabela 'vendas' e criar/alterar conforme necessário
        try:
            cursor.execute("SHOW COLUMNS FROM vendas")
            colunas_vendas = [col[0] for col in cursor.fetchall()]
        except Exception:
            # Tabela não existe, criar com todos os campos
            cursor.execute("""
                CREATE TABLE vendas (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    moto_id INT NOT NULL,
                    vendedor VARCHAR(255) NOT NULL,
                    data VARCHAR(50) NOT NULL,
                    preco_final DECIMAL(10,2) NULL,
                    cnh_path VARCHAR(255) NULL,
                    garantia_path VARCHAR(255) NULL,
                    endereco_path VARCHAR(255) NULL,
                    CONSTRAINT fk_vendas_motos FOREIGN KEY (moto_id) REFERENCES motos(id)
                )
            """)
            conn.commit()
            colunas_vendas = ["id","moto_id","vendedor","data","preco_final","cnh_path","garantia_path","endereco_path"]

        # Adicionar colunas novas em 'vendas' se faltarem
        for nome_coluna, tipo_coluna in [
            ("preco_final", "DECIMAL(10,2)"),
            ("cnh_path", "VARCHAR(255)"),
            ("garantia_path", "VARCHAR(255)"),
            ("endereco_path", "VARCHAR(255)")
        ]:
            if nome_coluna not in colunas_vendas:
                print(f"Aplicando migração: Adicionando coluna '{nome_coluna}' à tabela 'vendas'.")
                cursor.execute(f"ALTER TABLE vendas ADD COLUMN {nome_coluna} {tipo_coluna} NULL")
                conn.commit()
    except Exception as e:
        print(f"Erro na migração: {e}")
    finally:
        conn.close()


def iniciar_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INT AUTO_INCREMENT PRIMARY KEY,
            nome VARCHAR(255) UNIQUE,
            senha VARCHAR(255),
            tipo VARCHAR(50),
            email VARCHAR(255) UNIQUE
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS clientes (
            id INT AUTO_INCREMENT PRIMARY KEY,
            nome VARCHAR(255) NOT NULL,
            cpf VARCHAR(255) NOT NULL UNIQUE,
            telefone VARCHAR(255),
            email VARCHAR(255)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS motos (
            id INT AUTO_INCREMENT PRIMARY KEY,
            marca VARCHAR(255),
            modelo VARCHAR(255),
            ano INT,
            cor VARCHAR(255),
            km DECIMAL(10,2),
            preco DECIMAL(10,2),
            placa VARCHAR(255),
            combustivel VARCHAR(255),
            status VARCHAR(255),
            renavam VARCHAR(255),
            chassi VARCHAR(255),
            doc_moto VARCHAR(255),
            documento_fornecedor VARCHAR(255),
            comprovante_residencia VARCHAR(255),
            data_cadastro DATE,
            hora_cadastro TIME,
            nome_cliente VARCHAR(255),
            cpf_cliente VARCHAR(255),
            rua_cliente TEXT,
            cep_cliente VARCHAR(255),
            celular_cliente VARCHAR(255),
            referencia VARCHAR(255),
            celular_referencia VARCHAR(255),
            debitos TEXT,
            observacoes TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS vendas (
            id INT AUTO_INCREMENT PRIMARY KEY,
            moto_id INT,
            vendedor VARCHAR(255),
            data VARCHAR(255)
        )
    """)
    

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS categorias_financeiras (
            id INT AUTO_INCREMENT PRIMARY KEY,
            nome VARCHAR(255) NOT NULL UNIQUE
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS receitas (
            id INT AUTO_INCREMENT PRIMARY KEY,
            categoria VARCHAR(255) NOT NULL,
            adicionado_em VARCHAR(255) NOT NULL,
            valor DECIMAL(10,2) NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS gastos (
            id INT AUTO_INCREMENT PRIMARY KEY,
            categoria VARCHAR(255) NOT NULL,
            retirado_em VARCHAR(255) NOT NULL,
            valor DECIMAL(10,2) NOT NULL
        )
    """)

    # Criar tabela de vendas se não existir (com campos estendidos)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS vendas (
            id INT AUTO_INCREMENT PRIMARY KEY,
            moto_id INT NOT NULL,
            vendedor VARCHAR(255) NOT NULL,
            data VARCHAR(50) NOT NULL,
            preco_final DECIMAL(10,2) NULL,
            cnh_path VARCHAR(255) NULL,
            garantia_path VARCHAR(255) NULL,
            endereco_path VARCHAR(255) NULL,
            CONSTRAINT fk_vendas_motos FOREIGN KEY (moto_id) REFERENCES motos(id)
        )
    """)

    conn.commit()
    conn.close()

# Autenticação
def verificar_login(nome, senha):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT tipo FROM usuarios WHERE nome = %s AND senha = %s", (nome, senha))
    resultado = cursor.fetchone()
    conn.close()
    return resultado[0] if resultado else None

def get_usuario(nome):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT senha, tipo FROM usuarios WHERE nome = %s", (nome,))
    resultado = cursor.fetchone()
    conn.close()
    return resultado

def get_todos_usuarios():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, nome, email, tipo FROM usuarios")
    usuarios = cursor.fetchall()
    conn.close()
    return usuarios

def excluir_usuario(usuario_id):
    """Exclui um usuário pelo ID (sem restrição por tipo/ID)."""
    conn = get_db_connection()
    cursor = conn.cursor()
    # Verifica existência para retornar False se não existir
    cursor.execute("SELECT id FROM usuarios WHERE id = %s", (usuario_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return False

def atualizar_preco_venda_ultima(moto_id: int, preco_final: float) -> bool:
    """Atualiza o campo 'preco_final' da venda mais recente para a moto.
    Retorna True se atualizou, False se não encontrou venda.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM vendas WHERE moto_id = %s ORDER BY id DESC LIMIT 1", (moto_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return False
        venda_id = row[0]
        cursor.execute("UPDATE vendas SET preco_final = %s WHERE id = %s", (preco_final, venda_id))
        conn.commit()
        conn.close()
        return True
    except Exception:
        try:
            conn.close()
        except Exception:
            pass
        return False

def atualizar_garantia_venda(moto_id: int, garantia_path: str) -> bool:
    """Atualiza o campo garantia_path da venda mais recente (maior id) para a moto informada."""
    conn = get_db_connection()
    cursor = conn.cursor()
    # Encontrar a última venda desta moto
    cursor.execute("SELECT id FROM vendas WHERE moto_id = %s ORDER BY id DESC LIMIT 1", (moto_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return False
    venda_id = row[0]
    cursor.execute("UPDATE vendas SET garantia_path = %s WHERE id = %s", (garantia_path, venda_id))
    conn.commit()
    conn.close()
    return True
    cursor.execute("DELETE FROM usuarios WHERE id = %s", (usuario_id,))
    conn.commit()
    conn.close()
    return True

# === Clientes ===
def listar_clientes():
    """Retorna lista de clientes (id, nome, cpf, telefone, email)."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, nome, cpf, telefone, email FROM clientes ORDER BY nome ASC")
    rows = cursor.fetchall()
    conn.close()
    return rows

def atualizar_senha_por_id(usuario_id, nova_senha):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE usuarios SET senha = %s WHERE id = %s", (nova_senha, usuario_id))
    conn.commit()
    conn.close()

def criar_usuario(nome, senha, email, tipo="vendedor"):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO usuarios (nome, senha, email, tipo) VALUES (%s, %s, %s, %s)", (nome, senha, email, tipo))
        conn.commit()
        return True
    except mysql.connector.IntegrityError:
        # Retorna False se o nome ou email já existir
        return False
    finally:
        conn.close()

def ensure_usuarios_basicos():
    """Cria usuários básicos apenas se a tabela 'usuarios' estiver vazia."""
    conn = get_db_connection()
    cursor = conn.cursor()
    # Se já houver qualquer usuário, não cria nada
    try:
        cursor.execute("SELECT COUNT(*) FROM usuarios")
        total = cursor.fetchone()[0]
        if total and total > 0:
            conn.close()
            return
        cursor.execute(
            "INSERT INTO usuarios (nome, senha, email, tipo) VALUES (%s, %s, %s, %s)",
            ("admin", "1234", "admin@example.com", "admin")
        )
        cursor.execute(
            "INSERT INTO usuarios (nome, senha, email, tipo) VALUES (%s, %s, %s, %s)",
            ("vendedor", "1234", "vendedor@example.com", "vendedor")
        )
        conn.commit()
        print("Usuários padrão criados: admin/1234 e vendedor/1234")
    except Exception as e:
        print(f"Falha ao garantir usuários básicos: {e}")
    finally:
        conn.close()

def gerar_pdf_garantia(moto_id, venda_id=None):
    """
    Gera o PDF de garantia preenchido para a moto informada, salvando em static/garantia_moto_{moto_id}.pdf
    """
    import os
    import datetime
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    from reportlab.pdfbase import pdfmetrics
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT marca, modelo, ano, cor, placa, renavam, km, nome_cliente, cpf_cliente, rua_cliente, cep_cliente, data_cadastro FROM motos WHERE id = %s", (moto_id,))
    row = cursor.fetchone()
    # Buscar data da venda
    data_venda_str = None
    if venda_id:
        cursor.execute("SELECT data FROM vendas WHERE id = %s", (venda_id,))
        r = cursor.fetchone()
        data_venda_str = r[0] if r else None
    else:
        cursor.execute("SELECT data FROM vendas WHERE moto_id = %s ORDER BY id DESC LIMIT 1", (moto_id,))
        r = cursor.fetchone()
        data_venda_str = r[0] if r else None
    conn.close()
    if not row:
        print(f"Moto com id {moto_id} não encontrada para gerar garantia.")
        return None
    (marca, modelo, ano, cor, placa, renavam, km, nome_cliente, cpf_cliente, rua_cliente, cep_cliente, data_cadastro) = row
    # Dados fixos do vendedor (MIL GIROS MOTOS)
    vendedor_nome = "MIL GIROS MOTOS"
    vendedor_cnpj = "45.836.587/0001-01"
    vendedor_endereco = (
        "Itapecerica da Serra - Rod. Salvador de Leone, 2030, loja 4, "
        "Bairro Embu Mirim, Centro, CEP 06853-000"
    )
    # Nome do arquivo (usar caminho absoluto da pasta static ao lado deste módulo)
    base_dir = os.path.dirname(__file__)
    static_abs = os.path.join(base_dir, "static")
    os.makedirs(static_abs, exist_ok=True)
    nome_arquivo = os.path.join(static_abs, f"garantia_moto_{moto_id}.pdf")
    # Helpers
    def mes_extenso_pt(m):
        meses = [
            "JANEIRO", "FEVEREIRO", "MARÇO", "ABRIL", "MAIO", "JUNHO",
            "JULHO", "AGOSTO", "SETEMBRO", "OUTUBRO", "NOVEMBRO", "DEZEMBRO"
        ]
        return meses[m-1]

    def data_extenso(dt: datetime.date):
        return f"{dt.day} de {mes_extenso_pt(dt.month)} de {dt.year}"

    def parse_data(data_str: str):
        if not data_str:
            return None
        formatos = ["%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"]
        for fmt in formatos:
            try:
                return datetime.datetime.strptime(data_str, fmt).date()
            except ValueError:
                continue
        return None

    def wrap_text(texto, max_width, font_name="Helvetica", font_size=12):
        palavras = texto.split()
        linhas, atual = [], ""
        for p in palavras:
            teste = (atual + (" " if atual else "") + p)
            w = pdfmetrics.stringWidth(teste, font_name, font_size)
            if w <= max_width:
                atual = teste
            else:
                if atual:
                    linhas.append(atual)
                atual = p
        if atual:
            linhas.append(atual)
        return linhas

    c = canvas.Canvas(nome_arquivo, pagesize=A4)
    largura, altura = A4
    margem_esq = 50
    margem_dir = 50
    largura_util = largura - margem_esq - margem_dir
    y = altura - 60

    # Título
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(largura/2, y, "TERMO DE GARANTIA")
    y -= 18
    c.setFont("Helvetica-Bold", 12)
    c.drawCentredString(largura/2, y, "RESPONSABILIDADE- Veículos Semi Novos")
    y -= 24

    c.setFont("Helvetica", 11)
    paragrafos = [
        "Declaramos que o veículo abaixo descrito foi vistoriado em nossa Oficina ou oficina terceirizada e encontra-se em condições normais de uso, dirigibilidade e segurança. Quando o veículo estiver na garantia do fabricante este deverá acompanhá-lo diretamente ao concessionário autorizado ou, se preferir por nosso intermédio, concedemos ao comprador do veículo usado garantia que terá início na data da entrega do veículo e término após decorrido 03 (três) meses ou aos 3.000 km (3 mil quilômetros) percorridos, prevalecendo o que ocorrer primeiro.",
        "1- Garantia de Motor e Câmbio: a) A nossa obrigação, nos termos desta garantia, é recondicionarmos os conjuntos de motor e câmbio, caso apresentem problemas; b) Os reparos objeto da garantia serão efetuados sem qualquer despesa para o comprador, desde que os serviços sejam feitos por esta empresa ou por ela autorizados quando houver necessidade de serem executados por terceiros; c) Este certificado deve ser apresentado nos casos de solicitação de reparos, dentro do prazo de garantia;",
        "2- A Garantia será automaticamente cancelada nos casos abaixo: a) Se o veículo for reparado por terceiros não autorizados por nós ou, caso haja tal autorização, os serviços não tenham sido aprovados por esta; b) Se as peças e componentes originais do veículo forem substituídas em oficina não autorizada pela vendedora; c) Se o veículo for submetido a abuso, sobrecarga, competições de qualquer natureza, uso inadequado, manutenção negligente (falta de manutenção preventiva); d) Se o veículo tiver, direta ou indiretamente, sofrido acidente que comprometa o defeito reclamado; e) Se o defeito reclamado for decorrente de mau uso (inclusive utilização de combustível inadequado); f) Se a troca de óleo e filtro não tiver sido efetuada de acordo com a recomendação do fabricante;",
        "3- Ficam excluídos desta garantia os itens abaixo relacionados: a) Os serviços de manutenção preventiva, regulagem de motor e faróis ou outros, tais como limpeza de bicos injetores, reaperto, alinhamento e balanceamento, etc.; b) Lâmpadas; c) Sistema de embreagem (disco, colar, platô); d) Sistema de freios (pastilhas, discos, lonas, cilindro mestre e reparos); e) Suspensão e seus respectivos componentes; f) Sistema de alimentação de combustível; g) Sistema elétrico; h) Alarmes originais e instalados; i) Sistema de som; j) Pneus, velas, filtros, correias e demais peças de reposição periódica; k) O comprador deverá efetuar as revisões periodicamente em intervalos a cada 10.000 km ou de acordo com manual do proprietário emitido pelo fabricante; l) O presente não cobre a prestação de serviços de guincho e similares; m) A garantia diz respeito ao veículo identificado abaixo e é válida somente quando assinada por representantes legais da loja.",
        "CONDIÇÕES GERAIS: O adquirente identificado declara, para fins de direito, em caráter irrevogável e irretratável, estar ciente e de acordo com o conteúdo deste documento; após testar o veículo abaixo descrito, comprova que o mesmo se encontra em perfeito estado de conservação e desempenho.",
        "MODIFICAÇÕES NA ELÉTRICA: A garantia do veículo será inválida caso sejam realizadas instalações de rastreadores ou alarmes, quaisquer outros tipos de dispositivos eletrônicos que não tenham autorização prévia da concessionária. Qualquer modificação não autorizada que comprometa o funcionamento original do veículo poderá resultar na perda da garantia.",
    ]

    for p in paragrafos:
        linhas = wrap_text(p, largura_util)
        for ln in linhas:
            # Se não houver espaço suficiente antes de desenhar a linha, quebra de página
            if y < 120:
                c.showPage()
                c.setFont("Helvetica", 11)
                y = altura - 60
            c.drawString(margem_esq, y, ln)
            y -= 16
        # Espaço extra entre parágrafos
        if y < 120:
            c.showPage()
            c.setFont("Helvetica", 11)
            y = altura - 60
        y -= 6

    # Bloco de dados do veículo e comprador
    dados = [
        f"MARCA/MODELO: {str(marca or '')} / {str(modelo or '')}",
        f"ANO FAB/MODELO: {str(ano or '')}",
        f"COR: {str(cor or '')}",
        f"PLACA: {str(placa or '')}",
        f"RENAVAM: {str(renavam) if renavam else '-'}",
        f"KM: {str(km or '')}",
        "",
        f"Dados do Vendedor: {vendedor_nome} inscrito no CNPJ nº {vendedor_cnpj}",
        f"Endereço: {vendedor_endereco}",
        "",
        "Dados do Comprador:",
        f"Nome: {str(nome_cliente or '')}",
        f"CPF: {str(cpf_cliente or '')}",
        f"RUA: {str(rua_cliente or '')}",
        f"CEP: {str(cep_cliente or '')}",
    ]
    c.setFont("Helvetica", 11)
    for ln in dados:
        linhas = wrap_text(ln, largura_util)
        for l in linhas:
            if y < 120:
                c.showPage()
                c.setFont("Helvetica", 11)
                y = altura - 60
            c.drawString(margem_esq, y, l)
            y -= 16

    # Rodapé com local e data por extenso
    data_compra = parse_data(data_venda_str) or datetime.date.today()
    cidade = "Itapecerica da Serra, SP"
    # Texto longo do rodapé: quebrar em linhas e paginar
    rodape_texto = (
        "E, por estarem assim justas e contratadas, as partes assinam e rubricam o presente contrato, "
        "em duas vias de igual teor, para que produza seus regulares efeitos de direito."
    )
    for l in wrap_text(rodape_texto, largura_util):
        if y < 120:
            c.showPage()
            c.setFont("Helvetica", 11)
            y = altura - 60
        c.drawString(margem_esq, y, l)
        y -= 16
    # Espaço antes da data
    if y < 140:
        c.showPage()
        c.setFont("Helvetica", 11)
        y = altura - 60
    c.drawString(margem_esq, y, f"{cidade} {data_extenso(data_compra)}")
    y -= 28
    # Assinaturas (garantir espaço)
    if y < 120:
        c.showPage()
        c.setFont("Helvetica", 11)
        y = altura - 100
    c.drawString(margem_esq, y, "_________________________")
    c.drawString(margem_esq + 260, y, "______________________")
    y -= 14
    c.drawString(margem_esq, y, f"{str(nome_cliente or '')}")
    y -= 14
    c.drawString(margem_esq + 260, y, "1000GIROSMOTOS")
    y -= 14
    c.drawString(margem_esq + 260, y, f"CNPJ {vendedor_cnpj}")
    c.save()


def gerar_pdf_procuracao(moto_id, venda_id=None):
    """
    Gera o PDF de Procuração conforme modelo enviado, usando dados da moto e do comprador.
    Salva em static/procuracao_moto_{moto_id}.pdf
    """
    import os
    import datetime
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    from reportlab.pdfbase import pdfmetrics

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT marca, modelo, ano, cor, placa, renavam, chassi, km,
               nome_cliente, cpf_cliente, rua_cliente, cep_cliente
        FROM motos WHERE id = %s
        """,
        (moto_id,)
    )
    row = cursor.fetchone()
    # Buscar data da venda (se desejarmos usar em algum lugar futuramente)
    data_venda_str = None
    if venda_id:
        cursor.execute("SELECT data FROM vendas WHERE id = %s", (venda_id,))
        r = cursor.fetchone()
        data_venda_str = r[0] if r else None
    conn.close()
    if not row:
        print(f"Moto com id {moto_id} não encontrada para gerar procuração.")
        return None

    (marca, modelo, ano, cor, placa, renavam, chassi, km,
     nome_cliente, cpf_cliente, rua_cliente, cep_cliente) = row

    # Preparar arquivo em static
    base_dir = os.path.dirname(__file__)
    static_abs = os.path.join(base_dir, "static")
    os.makedirs(static_abs, exist_ok=True)
    nome_arquivo = os.path.join(static_abs, f"procuracao_moto_{moto_id}.pdf")

    # Helpers simples
    def wrap_text(texto, max_width, font_name="Helvetica", font_size=11):
        palavras = str(texto).split()
        linhas, atual = [], ""
        for p in palavras:
            teste = (atual + (" " if atual else "") + p)
            w = pdfmetrics.stringWidth(teste, font_name, font_size)
            if w <= max_width:
                atual = teste
            else:
                if atual:
                    linhas.append(atual)
                atual = p
        if atual:
            linhas.append(atual)
        return linhas

    c = canvas.Canvas(nome_arquivo, pagesize=A4)
    largura, altura = A4
    margem_esq = 50
    margem_dir = 50
    largura_util = largura - margem_esq - margem_dir
    y = altura - 60

    # Título
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(largura/2, y, "PROCURAÇÃO")
    y -= 24

    c.setFont("Helvetica", 11)
    # Cabeçalho com dados do OUTORGANTE (comprador)
    bloco_topo = [
        "Pelo presente instrumento particular de procuração, Eu:",
        f"{nome_cliente or ''}",
        f"CPF: {cpf_cliente or ''}",
        f"ENDEREÇO: {rua_cliente or ''}",
        f"CEP: {cep_cliente or ''}",
    ]
    for ln in bloco_topo:
        for l in wrap_text(ln, largura_util):
            c.drawString(margem_esq, y, l)
            y -= 16

    y -= 6
    # Linha do OUTORGADO (procurador fixo conforme modelo legal)
    bloco_outorgado = [
        "Nomeia e constitui-se bastante procurado HENRIQUE NASCIMENTO BITENCOURT",
        "CPF 396.894.918-81  Residente RODOVIA SALVADOR DE LEONE 2030"
        "CEP 06853-000",
        "a quem concedo os mais amplos, gerais e iluminados poderes a fim",
        "de que possa defender os direitos e interesses do (a) OUTORGANTE perante as",
        "repartições públicas em geral. Federais, Estaduais, Municipais, Autarquias,",
        "Oficiais de Registro Civil ou tabelionatos de notas, SPTrans, despachante,",
        "companhias de seguro, notadamente repartições de transito em geral, DETRAN/",
        "CONTRAN/ CIRETRAN/ DENATRAN, DTP e demais órgãos autorizados de",
        "transito em qualquer cidade do território nacional, podendo solicitar 2º via de",
        "CRV e CRLV , assinar /endossar transferências ( DUT – Documento único de",
        "transferência ) , autorizar e acompanhar vistorias, efetuar pagamentos, receber",
        "pagamentos, receber os valores referente a venda do veículo seja a vista ou",
        "financiada, formular requerimentos, interpor recursos, reclamar, desistir,",
        "solicitar, cópias de processos, firmar declaração de venda , além de ter acesso a",
        "documentos de qualquer natureza, referente exclusivamente ao VEICULO",
        "descrito abaixo.",
    ]
    for ln in bloco_outorgado:
        for l in wrap_text(ln, largura_util):
            c.drawString(margem_esq, y, l)
            y -= 16

    y -= 8
    c.setFont("Helvetica-Bold", 11)
    c.drawString(margem_esq, y, "Cláusula de Responsabilidade por Débitos Anteriores")
    y -= 18
    c.setFont("Helvetica", 11)
    clausulas = [
        "Declaro que qualquer débito existente antes da venda, como multas, são de",
        "minha inteira responsabilidade.",
        "Caso venha cair débitos e eu não regularize os mesmos, autorizo expressamente",
        "que meu nome seja negativado em órgãos de proteção ao crédito (SPC,",
        "SERASA, etc.), conforme já acordado neste documento.",
    ]
    for ln in clausulas:
        for l in wrap_text(ln, largura_util):
            c.drawString(margem_esq, y, l)
            y -= 16

    y -= 10
    c.setFont("Helvetica-Bold", 11)
    c.drawString(margem_esq, y, "MARCA/MODELO:")
    c.setFont("Helvetica", 11)
    c.drawString(margem_esq + 120, y, f"{marca or ''} / {modelo or ''}")
    y -= 16
    c.setFont("Helvetica-Bold", 11)
    c.drawString(margem_esq, y, "ANO/MODELO:")
    c.setFont("Helvetica", 11)
    c.drawString(margem_esq + 120, y, f"{ano or ''}")
    y -= 16
    c.setFont("Helvetica-Bold", 11)
    c.drawString(margem_esq, y, "COR:")
    c.setFont("Helvetica", 11)
    c.drawString(margem_esq + 120, y, f"{cor or ''}")
    y -= 16
    c.setFont("Helvetica-Bold", 11)
    c.drawString(margem_esq, y, "PLACA:")
    c.setFont("Helvetica", 11)
    c.drawString(margem_esq + 120, y, f"{placa or ''}")
    y -= 16
    c.setFont("Helvetica-Bold", 11)
    c.drawString(margem_esq, y, "RENAVAM:")
    c.setFont("Helvetica", 11)
    c.drawString(margem_esq + 120, y, f"{renavam or ''}")
    y -= 16
    c.setFont("Helvetica-Bold", 11)
    c.drawString(margem_esq, y, "CHASSI:")
    c.setFont("Helvetica", 11)
    c.drawString(margem_esq + 120, y, f"{chassi or ''}")
    y -= 24

    obs = "Nos termos da Portaria Detran/SP nº 1680, cap II, art 8, Parágrafo VI."
    for l in wrap_text(obs, largura_util):
        c.drawString(margem_esq, y, l)
        y -= 16

    y -= 24
    c.drawString(margem_esq, y, "_________________________________________")
    y -= 16
    c.drawString(margem_esq, y, "Assinar e reconhecer firma por autenticidade")

    c.save()
    if os.path.exists(nome_arquivo):
        return nome_arquivo
    else:
        print(f"Erro: PDF não foi criado em {nome_arquivo}")
        return None

# Motos
def cadastrar_moto(dados):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO motos (
            marca, modelo, ano, cor, km, preco, placa, combustivel, status,
            renavam, chassi, doc_moto, documento_fornecedor, comprovante_residencia, data_cadastro, hora_cadastro,
            nome_cliente, cpf_cliente, rua_cliente, cep_cliente, celular_cliente, referencia, celular_referencia, debitos, observacoes
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        dados["marca"], dados["modelo"], dados["ano"], dados["cor"],
        dados["km"], dados["preco"], dados["placa"], dados["combustivel"], dados["status"],
        dados.get("renavam"), dados.get("chassi"), dados.get("doc_moto"), dados.get("documento_fornecedor"),
        dados.get("comprovante_residencia"), dados.get("data_cadastro"),
        dados.get("hora_cadastro"), dados.get("nome_cliente"),
        dados.get("cpf_cliente"), dados.get("rua_cliente"), dados.get("cep_cliente"),
        dados.get("celular_cliente"), dados.get("referencia"),
        dados.get("celular_referencia"), dados.get("debitos"),
        dados.get("observacoes")
    ))
    moto_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return moto_id

def atualizar_campos_comprador(moto_id: int, nome: str = None, cpf: str = None, rua: str = None, cep: str = None):
    """Atualiza apenas os campos do comprador na tabela motos, se valores forem informados."""
    conn = get_db_connection()
    cursor = conn.cursor()
    sets = []
    params = []
    if nome is not None and nome != "":
        sets.append("nome_cliente = %s")
        params.append(nome)
    if cpf is not None and cpf != "":
        sets.append("cpf_cliente = %s")
        params.append(cpf)
    if rua is not None and rua != "":
        sets.append("rua_cliente = %s")
        params.append(rua)
    if cep is not None and cep != "":
        sets.append("cep_cliente = %s")
        params.append(cep)
    if sets:
        query = "UPDATE motos SET " + ", ".join(sets) + " WHERE id = %s"
        params.append(moto_id)
        cursor.execute(query, params)
        conn.commit()
    conn.close()

def listar_motos():
    conn = get_db_connection()
    cursor = conn.cursor()
    # Selecionar colunas em ordem explícita e estável para manter índices usados nas templates
    cursor.execute(
        """
        SELECT id, marca, modelo, ano, cor, km, preco, placa, combustivel, status,
               renavam, chassi, doc_moto, documento_fornecedor, comprovante_residencia,
               data_cadastro, hora_cadastro, nome_cliente, cpf_cliente, rua_cliente,
               cep_cliente, celular_cliente, referencia, celular_referencia, debitos, observacoes
        FROM motos
        """
    )
    motos = cursor.fetchall()
    conn.close()
    return motos

def get_motos_basico():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, marca, modelo, ano, cor, preco FROM motos ORDER BY id DESC")
    motos = cursor.fetchall()
    conn.close()
    return motos

def buscar_moto(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    # Selecionar colunas em ordem explícita e estável para manter índices usados nas templates
    cursor.execute(
        """
        SELECT id, marca, modelo, ano, cor, km, preco, placa, combustivel, status,
               renavam, chassi, doc_moto, documento_fornecedor, comprovante_residencia,
               data_cadastro, hora_cadastro, nome_cliente, cpf_cliente, rua_cliente,
               cep_cliente, celular_cliente, referencia, celular_referencia, debitos, observacoes
        FROM motos
        WHERE id = %s
        """,
        (id,)
    )
    moto = cursor.fetchone()
    conn.close()
    return moto

def existe_moto_com_placa(placa: str, excluir_id: int | None = None) -> bool:
    """Retorna True se já existe uma moto com a mesma placa (normalizada) diferente de excluir_id.

    A normalização remove hífens, espaços e aplica UPPER para evitar duplicidades por formatação.
    Placas vazias não são consideradas para unicidade (retorna False).
    """
    try:
        if not placa or not str(placa).strip():
            return False
        conn = get_db_connection()
        cursor = conn.cursor()
        if excluir_id is None:
            cursor.execute(
                """
                SELECT id FROM motos
                WHERE REPLACE(REPLACE(UPPER(placa), '-', ''), ' ', '') = REPLACE(REPLACE(UPPER(%s), '-', ''), ' ', '')
                LIMIT 1
                """,
                (placa,)
            )
        else:
            cursor.execute(
                """
                SELECT id FROM motos
                WHERE REPLACE(REPLACE(UPPER(placa), '-', ''), ' ', '') = REPLACE(REPLACE(UPPER(%s), '-', ''), ' ', '')
                  AND id <> %s
                LIMIT 1
                """,
                (placa, excluir_id)
            )
        row = cursor.fetchone()
        conn.close()
        return bool(row)
    except Exception:
        try:
            conn.close()
        except Exception:
            pass
        return False

def atualizar_moto(id, dados):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE motos SET
          marca = %s,
          modelo = %s,
          ano = %s,
          cor = %s,
          km = %s,
          preco = %s,
          placa = %s,
          combustivel = %s,
          status = %s,
          renavam = %s,
          chassi = %s,
          doc_moto = COALESCE(%s, doc_moto),
          documento_fornecedor = COALESCE(%s, documento_fornecedor),
          comprovante_residencia = COALESCE(%s, comprovante_residencia),
          data_cadastro = %s,
          hora_cadastro = %s,
          nome_cliente = %s,
          cpf_cliente = %s,
          rua_cliente = %s,
          cep_cliente = %s,
          celular_cliente = %s,
          referencia = %s,
          celular_referencia = %s,
          debitos = %s,
          observacoes = %s
        WHERE id = %s
    """, (
        dados["marca"], dados["modelo"], dados["ano"], dados["cor"],
        dados["km"], dados["preco"], dados["placa"], dados["combustivel"],
        dados["status"],
        dados.get("renavam"),
        dados.get("chassi"),
        dados.get("doc_moto"),
        dados.get("documento_fornecedor"),
        dados.get("comprovante_residencia"),
        dados.get("data_cadastro"),
        dados.get("hora_cadastro"),
        dados.get("nome_cliente"),
        dados.get("cpf_cliente"),
        dados.get("rua_cliente"),
        dados.get("cep_cliente"),
        dados.get("celular_cliente"),
        dados.get("referencia"),
        dados.get("celular_referencia"),
        dados.get("debitos"),
        dados.get("observacoes"),
        id
    ))
    conn.commit()
    conn.close()
    
def filtrar_motos_completo(filtros):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Selecionar colunas em ordem explícita e estável para manter índices usados nas templates
    query = (
        "SELECT id, marca, modelo, ano, cor, km, preco, placa, combustivel, status, "
        "renavam, chassi, doc_moto, documento_fornecedor, comprovante_residencia, "
        "data_cadastro, hora_cadastro, nome_cliente, cpf_cliente, rua_cliente, "
        "cep_cliente, celular_cliente, referencia, celular_referencia, debitos, observacoes "
        "FROM motos WHERE 1=1"
    )
    params = []

    if filtros["marca_modelo"]:
        query += " AND (marca LIKE %s OR modelo LIKE %s)"
        valor = f"%{filtros['marca_modelo']}%"
        params += [valor, valor]
    if filtros["placa"]:
        query += " AND placa LIKE %s"
        params.append(f"%{filtros['placa']}%")
    if filtros.get("renavam"):
        query += " AND renavam LIKE %s"
        params.append(f"%{filtros['renavam']}%")
    if filtros["combustivel"]:
        query += " AND combustivel = %s"
        params.append(filtros["combustivel"])
    if filtros["ano_min"]:
        query += " AND ano >= %s"
        params.append(int(filtros["ano_min"]))
    if filtros["ano_max"]:
        query += " AND ano <= %s"
        params.append(int(filtros["ano_max"]))
    if filtros["km_min"]:
        query += " AND km >= %s"
        params.append(float(filtros["km_min"]))
    if filtros["km_max"]:
        query += " AND km <= %s"
        params.append(float(filtros["km_max"]))
    if filtros["preco_min"]:
        query += " AND preco >= %s"
        params.append(float(filtros["preco_min"]))
    if filtros["preco_max"]:
        query += " AND preco <= %s"
        params.append(float(filtros["preco_max"]))
    if filtros["status"]:
        st = str(filtros["status"]).strip().lower()
        # Tratar acentuação para 'disponível' vs 'disponivel'
        if st in ("disponível", "disponivel"):
            query += " AND (status = %s OR status = %s)"
            params.extend(["disponível", "disponivel"])
        else:
            query += " AND status = %s"
            params.append(filtros["status"])
    elif filtros.get("estoque_apenas"):
        # Quando não há status específico, mas queremos apenas itens em estoque (disponíveis + consignado)
        query += " AND status IN ('disponível','disponivel','consignado')"

    # Deduplicar por placa (opcional): mantém apenas o registro mais recente (maior id) por placa
    if filtros.get("dedup_por_status"):
        # Deduplica por placa dentro do mesmo status, mas não remove registros com placa vazia/nula
        # Normaliza placa removendo hífens e espaços e aplicando UPPER
        query += (
            " AND ("
            "   REPLACE(REPLACE(UPPER(COALESCE(placa,'')), '-', ''), ' ', '') = ''"
            "   OR id = ("
            "       SELECT MAX(m2.id) FROM motos m2"
            "       WHERE REPLACE(REPLACE(UPPER(COALESCE(m2.placa,'')), '-', ''), ' ', '') = REPLACE(REPLACE(UPPER(COALESCE(motos.placa,'')), '-', ''), ' ', '')"
            "         AND m2.status = motos.status"
            "   )"
            " )"
        )
    elif filtros.get("dedup_placa"):
        # Normaliza placa removendo hífens e espaços e usando UPPER para evitar duplicidades por formatação
        query += (
            " AND id = ("
            "   SELECT MAX(m2.id) FROM motos m2"
            "   WHERE REPLACE(REPLACE(UPPER(m2.placa), '-', ''), ' ', '') = REPLACE(REPLACE(UPPER(motos.placa), '-', ''), ' ', '')"
            " )"
        )

    # Ordenar por ID crescente para facilitar leitura e evitar confusão visual
    query += " ORDER BY id ASC"
    cursor.execute(query, params)
    resultado = cursor.fetchall()
    conn.close()
    return resultado

def excluir_moto(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM motos WHERE id = %s", (id,))
    conn.commit()
    conn.close()

# Dashboard
def get_stats_estoque():
    conn = get_db_connection()
    cursor = conn.cursor()
    # Considerar 'disponível', 'disponivel' (sem acento) e 'consignado' como estoque
    # Usar mesma lógica de deduplicação da listagem: dedup por placa NORMALIZADA dentro do mesmo status,
    # porém NÃO deduplicar quando a placa estiver vazia/nula (conta todos os registros de placa vazia)
    cursor.execute(
        """
        SELECT COUNT(m.id) AS qtd, SUM(m.preco) AS soma
        FROM motos m
        WHERE m.status IN ('disponível','disponivel','consignado')
          AND (
              REPLACE(REPLACE(UPPER(COALESCE(m.placa,'')), '-', ''), ' ', '') = ''
              OR m.id = (
                    SELECT MAX(m2.id) FROM motos m2
                    WHERE m2.status = m.status
                      AND REPLACE(REPLACE(UPPER(COALESCE(m2.placa,'')), '-', ''), ' ', '') = REPLACE(REPLACE(UPPER(COALESCE(m.placa,'')), '-', ''), ' ', '')
              )
          )
        """
    )
    dados = cursor.fetchone()
    conn.close()
    # Retorna (quantidade, soma) ou (0, 0) se não houver motos
    return dados if dados and dados[0] is not None else (0, 0)

def get_stats_vendas_mes():
    conn = get_db_connection()
    cursor = conn.cursor()
    # DATE_FORMAT para MySQL
    cursor.execute("""
        SELECT COUNT(v.id), SUM(m.preco)
        FROM vendas v
        JOIN motos m ON v.moto_id = m.id
        WHERE DATE_FORMAT(STR_TO_DATE(v.data, '%Y-%m-%d'), '%Y-%m') = DATE_FORMAT(NOW(), '%Y-%m')
    """)
    dados = cursor.fetchone()
    conn.close()
    return dados if dados and dados[0] is not None else (0, 0)

# Vendas
def registrar_venda(moto_id, vendedor, data, preco_final=None, cnh_path=None, garantia_path=None, endereco_path=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    # Permitir venda quando a moto estiver 'disponível' (com e sem acento) ou 'consignado'
    cursor.execute("SELECT id FROM motos WHERE id = %s AND status IN ('disponível','disponivel','consignado')", (moto_id,))
    if cursor.fetchone():
        cursor.execute("""
            INSERT INTO vendas (moto_id, vendedor, data, preco_final, cnh_path, garantia_path, endereco_path)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (moto_id, vendedor, data, preco_final, cnh_path, garantia_path, endereco_path))
        venda_id = cursor.lastrowid  # Pega o ID da venda recém-criada
        cursor.execute("UPDATE motos SET status = 'vendida' WHERE id = %s", (moto_id,))
        conn.commit()
        conn.close()
        return venda_id  # Retorna o ID da venda ao invés de True
    conn.close()
    return False

def atualizar_venda_campos(venda_id, preco_final=None, cnh_path=None, garantia_path=None, endereco_path=None):
    """Atualiza campos opcionais da venda (preço final e anexos)."""
    if not any([preco_final is not None, cnh_path, garantia_path, endereco_path]):
        return
    conn = get_db_connection()
    cursor = conn.cursor()
    sets = []
    params = []
    if preco_final is not None:
        sets.append("preco_final = %s")
        params.append(preco_final)
    if cnh_path:
        sets.append("cnh_path = %s")
        params.append(cnh_path)
    if garantia_path:
        sets.append("garantia_path = %s")
        params.append(garantia_path)
    if endereco_path:
        sets.append("endereco_path = %s")
        params.append(endereco_path)
    if sets:
        query = "UPDATE vendas SET " + ", ".join(sets) + " WHERE id = %s"
        params.append(venda_id)
        cursor.execute(query, params)
        conn.commit()
    conn.close()

def atualizar_data_venda_ultima(moto_id: int, data_venda: str) -> bool:
    """
    Atualiza o campo 'data' da venda mais recente (maior id) para a moto informada.
    Espera 'data_venda' no formato ISO 'YYYY-MM-DD'.
    Retorna True se atualizou, False se não encontrou venda.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM vendas WHERE moto_id = %s ORDER BY id DESC LIMIT 1", (moto_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return False
        venda_id = row[0]
        cursor.execute("UPDATE vendas SET data = %s WHERE id = %s", (data_venda, venda_id))
        conn.commit()
        conn.close()
        return True
    except Exception:
        # Em caso de erro, garantir fechamento e retornar False
        try:
            conn.close()
        except Exception:
            pass
        return False

# Relatório
def gerar_relatorio():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM motos ORDER BY id ASC")
    linhas = cursor.fetchall()

    estoque = []
    total_disponivel = 0
    total_vendida = 0

    for m in linhas:
        status = m[9] or "desconhecido"
        if status.lower() == "disponível":
            total_disponivel += 1
        elif status.lower() == "vendida":
            total_vendida += 1

        estoque.append((
            m[0], m[1] or "", m[2] or "", m[3] or 0, m[4] or "",
            m[5] or 0, m[6] or 0, m[7] or "", m[8] or "", status
        ))

    # Contar vendas por vendedor apenas para motos existentes (exclui motos deletadas)
    cursor.execute(
        """
        SELECT v.vendedor, COUNT(m.id)
        FROM vendas v
        INNER JOIN motos m ON v.moto_id = m.id
        GROUP BY v.vendedor
        """
    )
    vendas = cursor.fetchall()

    conn.close()
    total_geral = total_disponivel + total_vendida
    resumo = {
        "total_disponivel": total_disponivel,
        "total_vendida": total_vendida,
        "total_geral": total_geral
    }

    return estoque, vendas, resumo

# Recibo
def detalhes_venda(moto_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT m.id, m.marca, m.modelo, m.ano, m.cor,
               m.placa, m.preco, m.km,
               v.vendedor, v.data, v.preco_final, v.id
        FROM motos m
        JOIN vendas v ON m.id = v.moto_id
        WHERE m.id = %s
        ORDER BY v.id DESC
        LIMIT 1
    """, (moto_id,))
    dados = cursor.fetchone()
    conn.close()
    return dados

def detalhes_venda_por_id(venda_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT m.id, m.marca, m.modelo, m.ano, m.cor,
               m.placa, m.preco, m.km,
               v.vendedor, v.data, v.id, v.preco_final
        FROM motos m
        JOIN vendas v ON m.id = v.moto_id
        WHERE v.id = %s
    """, (venda_id,))
    dados = cursor.fetchone()
    conn.close()
    return dados

def gerar_pdf_recibo(moto_id):
    import os
    try:
        dados = detalhes_venda(moto_id)
        if not dados:
            print(f"Erro: Dados da venda não encontrados para moto_id {moto_id}")
            return None

        # Garantir que a pasta static existe
        os.makedirs("static", exist_ok=True)
        
        nome_arquivo = os.path.join("static", f"recibo_moto_{moto_id}.pdf")
        print(f"Tentando criar PDF em: {os.path.abspath(nome_arquivo)}")
        
        c = canvas.Canvas(nome_arquivo, pagesize=A4)
        c.setFont("Helvetica", 12)
        largura, altura = A4
        y = altura - 100

        c.drawString(50, altura - 50, "Recibo de Compra e Venda de Moto")

        preco_final = dados[10] if len(dados) > 10 and dados[10] is not None else dados[6]
        texto = [
            f"Moto: {dados[1]} {dados[2]} ({dados[3]})",
            f"Cor: {dados[4]}",
            f"Placa: {dados[5]}",
            f"KM: {br_km_safe(dados[7])}",
            f"Identificador: {dados[0]} (Venda #{dados[11]})",
            f"Preço Final: {br_moeda_safe(preco_final)}",
            f"Vendedor: {dados[8]}",
            f"Data da Venda: {dados[9]}",
            "",
            "Declaro para os devidos fins que a motocicleta descrita acima foi negociada entre as partes.",
            "",
            "__________________________        __________________________",
            "Assinatura do Vendedor           Assinatura do Comprador"
        ]

        for linha in texto:
            c.drawString(50, y, linha)
            y -= 20

        c.save()
        
        # Verificar se o arquivo foi criado
        if os.path.exists(nome_arquivo):
            print(f"PDF criado com sucesso: {nome_arquivo}")
            return nome_arquivo
        else:
            print(f"Erro: PDF não foi criado em {nome_arquivo}")
            return None
            
    except Exception as e:
        print(f"Erro ao gerar PDF do recibo: {e}")
        return None

def gerar_html_recibo_por_venda_id(venda_id):
    """
    Gera um HTML do recibo de venda usando o ID da venda
    """
    import os
    try:
        # Buscar detalhes da venda
        detalhes = detalhes_venda_por_id(venda_id)
        if not detalhes:
            print(f"Venda com ID {venda_id} não encontrada")
            return None
        
        # Garantir que a pasta static existe
        os.makedirs("static", exist_ok=True)
        
        # Gerar nome do arquivo usando ID da venda
        nome_arquivo = os.path.join("static", f"recibo_venda_{venda_id}.html")
        print(f"Gerando HTML em: {os.path.abspath(nome_arquivo)}")
        
        # Formatação brasileira
        preco_final = detalhes[11] if len(detalhes) > 11 and detalhes[11] is not None else detalhes[6]
        preco_formatado = br_moeda_safe(preco_final)
        km_formatado = br_km_safe(detalhes[7])
        
        # Criar o HTML usando concatenação de strings para evitar problemas com f-strings
        html_content = '''<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Recibo de Venda - ''' + str(detalhes[10]) + '''</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .recibo {
            background-color: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 0 10px rgba(0,0,0,0.1);
        }
        .header {
            text-align: center;
            border-bottom: 2px solid #333;
            padding-bottom: 20px;
            margin-bottom: 30px;
        }
        .header h1 {
            color: #333;
            margin: 0;
        }
        .section {
            margin-bottom: 25px;
        }
        .section h2 {
            color: #555;
            border-bottom: 1px solid #ddd;
            padding-bottom: 5px;
        }
        .info-row {
            display: flex;
            justify-content: space-between;
            margin-bottom: 10px;
        }
        .label {
            font-weight: bold;
            color: #333;
        }
        .value {
            color: #666;
        }
        .preco {
            font-size: 24px;
            font-weight: bold;
            color: #28a745;
            text-align: center;
            background-color: #f8f9fa;
            padding: 15px;
            border-radius: 5px;
            margin: 20px 0;
        }
        .footer {
            text-align: center;
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #ddd;
            color: #888;
            font-size: 12px;
        }
        @media print {
            body {
                background-color: white;
            }
            .recibo {
                box-shadow: none;
            }
        }
    </style>
</head>
<body>
    <div class="recibo">
        <div class="header">
            <h1>🏍️ RECIBO DE VENDA</h1>
            <p>Sistema Motos Web</p>
        </div>
        
        <div class="section">
            <h2>📋 Informações da Venda</h2>
            <div class="info-row">
                <span class="label">ID da Venda:</span>
                <span class="value">''' + str(detalhes[10]) + '''</span>
            </div>
            <div class="info-row">
                <span class="label">Data:</span>
                <span class="value">''' + str(detalhes[9]) + '''</span>
            </div>
            <div class="info-row">
                <span class="label">Vendedor:</span>
                <span class="value">''' + str(detalhes[8]) + '''</span>
            </div>
        </div>
        
        <div class="section">
            <h2>🏍️ Motocicleta</h2>
            <div class="info-row">
                <span class="label">Marca:</span>
                <span class="value">''' + str(detalhes[1]) + '''</span>
            </div>
            <div class="info-row">
                <span class="label">Modelo:</span>
                <span class="value">''' + str(detalhes[2]) + '''</span>
            </div>
            <div class="info-row">
                <span class="label">Ano:</span>
                <span class="value">''' + str(detalhes[3]) + '''</span>
            </div>
            <div class="info-row">
                <span class="label">Cor:</span>
                <span class="value">''' + str(detalhes[4]) + '''</span>
            </div>
            <div class="info-row">
                <span class="label">Quilometragem:</span>
                <span class="value">''' + km_formatado + '''</span>
            </div>
        </div>
        
        <div class="preco">
            💰 VALOR TOTAL: ''' + preco_formatado + '''
        </div>
        
        <div class="footer">
            <p>Recibo gerado automaticamente em ''' + str(detalhes[8]) + '''</p>
            <p>Sistema Motos Web - Gestão de Vendas</p>
        </div>
    </div>
    
    <script>
        window.onload = function() {
            setTimeout(function() {
                window.print();
            }, 500);
        };
    </script>
</body>
</html>'''
        
        # Salvar o HTML
        with open(nome_arquivo, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        # Verificar se o arquivo foi criado
        if os.path.exists(nome_arquivo):
            print(f"HTML gerado com sucesso: {nome_arquivo}")
            return nome_arquivo
        else:
            print(f"Erro: HTML não foi criado em {nome_arquivo}")
            return None
            
    except Exception as e:
        print(f"Erro ao gerar HTML do recibo: {e}")
        import traceback
        traceback.print_exc()
        return None

def gerar_pdf_recibo_por_venda_id(venda_id):
    """
    Tenta gerar PDF, mas se falhar, gera HTML como alternativa
    """
    try:
        import os
        # Tentar gerar PDF primeiro
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
        
        # Buscar detalhes da venda
        detalhes = detalhes_venda_por_id(venda_id)
        if not detalhes:
            print(f"Venda com ID {venda_id} não encontrada")
            return None
        
        # Garantir que a pasta static existe
        os.makedirs("static", exist_ok=True)
        
        # Gerar nome do arquivo usando ID da venda
        nome_arquivo = os.path.join("static", f"recibo_venda_{venda_id}.pdf")
        print(f"Gerando PDF em: {os.path.abspath(nome_arquivo)}")
        
        # Criar o PDF
        c = canvas.Canvas(nome_arquivo, pagesize=A4)
        
        # Título
        c.setFont("Helvetica-Bold", 16)
        c.drawString(50, 800, "RECIBO DE VENDA - SISTEMA MOTOS")
        
        # Linha separadora
        c.line(50, 790, 550, 790)
        
        # Informações da venda
        c.setFont("Helvetica", 12)
        y = 760
        
        c.drawString(50, y, f"Venda ID: {detalhes[9]}")
        y -= 20
        c.drawString(50, y, f"Data: {detalhes[8]}")
        y -= 20
        c.drawString(50, y, f"Vendedor: {detalhes[7]}")
        y -= 30
        
        # Informações da moto
        c.setFont("Helvetica-Bold", 14)
        c.drawString(50, y, "MOTOCICLETA:")
        y -= 20
        c.setFont("Helvetica", 12)
        c.drawString(50, y, f"Marca: {detalhes[1]}")
        y -= 20
        c.drawString(50, y, f"Modelo: {detalhes[2]}")
        y -= 20
        c.drawString(50, y, f"Ano: {detalhes[3]}")
        y -= 20
        c.drawString(50, y, f"Cor: {detalhes[4]}")
        y -= 20
        c.drawString(50, y, f"KM: {detalhes[5]:,}".replace(",", "."))
        y -= 20
        
        # Preço em destaque
        c.setFont("Helvetica-Bold", 14)
        preco_formatado = br_moeda_safe(detalhes[6])
        c.drawString(50, y, f"PREÇO: {preco_formatado}")
        
        # Rodapé
        c.setFont("Helvetica", 10)
        c.drawString(50, 50, "Sistema Motos Web - Recibo gerado automaticamente")
        
        # Salvar o PDF
        c.save()
        
        # Verificar se o arquivo foi criado
        if os.path.exists(nome_arquivo):
            print(f"PDF gerado com sucesso: {nome_arquivo}")
            return nome_arquivo
        else:
            print(f"Erro: PDF não foi criado em {nome_arquivo}")
            return None
            
    except ImportError as e:
        print(f"ReportLab não disponível, gerando HTML: {e}")
        return gerar_html_recibo_por_venda_id(venda_id)
    except Exception as e:
        print(f"Erro ao gerar PDF, tentando HTML: {e}")
        return gerar_html_recibo_por_venda_id(venda_id)

## Funções de despesas removidas a pedido do usuário: registrar_despesa, listar_despesas,
## resumo_despesas_por_mes, gerar_pdf_despesas, total_despesas_por_ano

# CONTROLE FINANCEIRO - Funções para integração do app_flask
def inserir_categoria_financeira(nome):
    """Insere nova categoria financeira"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO categorias_financeiras (nome) VALUES (%s)", (nome,))
        conn.commit()
        return True
    except mysql.connector.IntegrityError:
        return False
    finally:
        conn.close()

def ver_categorias_financeiras():
    """Retorna todas as categorias financeiras"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM categorias_financeiras")
    categorias = cursor.fetchall()
    conn.close()
    return categorias

def deletar_categoria_financeira(categoria_id: int) -> bool:
    """Exclui uma categoria financeira pelo ID.
    Observação: receitas/gastos existentes não são alterados (armazenam o nome da categoria como texto).
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM categorias_financeiras WHERE id = %s", (categoria_id,))
    conn.commit()
    ok = cursor.rowcount > 0
    conn.close()
    return ok

def inserir_receita_financeira(categoria, data, valor):
    """Insere nova receita"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO receitas (categoria, adicionado_em, valor) VALUES (%s, %s, %s)", (categoria, data, valor))
    conn.commit()
    conn.close()

def inserir_gasto_financeiro(categoria, data, valor):
    """Insere novo gasto"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO gastos (categoria, retirado_em, valor) VALUES (%s, %s, %s)", (categoria, data, valor))
    conn.commit()
    conn.close()

def ver_receitas_financeiras():
    """Retorna todas as receitas"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM receitas ORDER BY id DESC")
    receitas = cursor.fetchall()
    conn.close()
    return receitas

def ver_receitas_financeiras_filtrado(periodo_ym: str):
    """Retorna receitas filtradas por mês (periodo_ym = 'YYYY-MM')."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT * FROM receitas
        WHERE DATE_FORMAT(STR_TO_DATE(adicionado_em, '%d/%m/%Y'), '%Y-%m') = %s
        ORDER BY id DESC
        """,
        (periodo_ym,)
    )
    receitas = cursor.fetchall()
    conn.close()
    return receitas

def ver_gastos_financeiros():
    """Retorna todos os gastos"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM gastos ORDER BY id DESC")
    gastos = cursor.fetchall()
    conn.close()
    return gastos

def ver_gastos_financeiros_filtrado(periodo_ym: str):
    """Retorna gastos filtrados por mês (periodo_ym = 'YYYY-MM')."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT * FROM gastos
        WHERE DATE_FORMAT(STR_TO_DATE(retirado_em, '%d/%m/%Y'), '%Y-%m') = %s
        ORDER BY id DESC
        """,
        (periodo_ym,)
    )
    gastos = cursor.fetchall()
    conn.close()
    return gastos

def atualizar_receita_financeira(id_receita, data=None, valor=None, categoria=None):
    """Atualiza campos da receita. Data deve vir no formato DD/MM/YYYY (compatível com inserção existente)."""
    if all(v is None or v == "" for v in [data, valor, categoria]):
        return False
    conn = get_db_connection()
    cursor = conn.cursor()
    sets = []
    params = []
    if categoria:
        sets.append("categoria = %s")
        params.append(categoria)
    if data:
        sets.append("adicionado_em = %s")
        params.append(data)
    if valor is not None:
        sets.append("valor = %s")
        params.append(valor)
    query = "UPDATE receitas SET " + ", ".join(sets) + " WHERE id = %s"
    params.append(id_receita)
    cursor.execute(query, params)
    conn.commit()
    conn.close()
    return True

def atualizar_gasto_financeiro(id_gasto, categoria=None, data=None, valor=None):
    """Atualiza campos do gasto. Data deve vir no formato DD/MM/YYYY (compatível com inserção existente)."""
    if all(v is None or v == "" for v in [categoria, data, valor]):
        return False
    conn = get_db_connection()
    cursor = conn.cursor()
    sets = []
    params = []
    if categoria:
        sets.append("categoria = %s")
        params.append(categoria)
    if data:
        sets.append("retirado_em = %s")
        params.append(data)
    if valor is not None:
        sets.append("valor = %s")
        params.append(valor)
    query = "UPDATE gastos SET " + ", ".join(sets) + " WHERE id = %s"
    params.append(id_gasto)
    cursor.execute(query, params)
    conn.commit()
    conn.close()
    return True

def deletar_receita_financeira(id_receita):
    """Deleta receita por ID"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM receitas WHERE id = %s", (id_receita,))
    conn.commit()
    conn.close()

def deletar_gasto_financeiro(id_gasto):
    """Deleta gasto por ID"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM gastos WHERE id = %s", (id_gasto,))
    conn.commit()
    conn.close()

def calcular_valores_financeiros():
    """Calcula valores para dashboard financeiro"""
    receitas = ver_receitas_financeiras()
    gastos = ver_gastos_financeiros()
    
    receita_total = sum(float(r[3]) for r in receitas)  # r[3] é o valor
    gastos_total = sum(float(g[3]) for g in gastos)     # g[3] é o valor
    saldo_total = receita_total - gastos_total
    
    return [receita_total, gastos_total, saldo_total]

def gastos_por_categoria():
    """Calcula gastos agrupados por categoria para gráfico"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT categoria, SUM(valor) FROM gastos GROUP BY categoria")
    dados = cursor.fetchall()
    conn.close()
    
    if not dados:
        return [[], []]
    
    categorias = [d[0] for d in dados]
    valores = [float(d[1]) for d in dados]
    
    return [categorias, valores]

def inicializar_categorias_padrao():
    """Inicializa categorias padrão se não existirem"""
    categorias_padrao = ['Alimentação', 'Transporte', 'Moradia', 'Saúde', 'Educação', 'Lazer', 'Outros']
    for categoria in categorias_padrao:
        inserir_categoria_financeira(categoria)