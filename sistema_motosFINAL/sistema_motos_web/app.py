from flask import Flask, render_template, request, redirect, session, send_file, flash, url_for
try:
    from flask_compress import Compress
except Exception:
    # Fallback no-op Compress if Flask-Compress is not available
    class Compress:  # type: ignore
        def __init__(self, *args, **kwargs):
            pass
from werkzeug.utils import secure_filename
from datetime import datetime
import database
import pandas as pd
import os
import uuid
import logging

app = Flask(__name__)
# Load secret key from environment for production, fallback for local dev
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "segredo123")

# Production-oriented settings
# Cache static files for 7 days, disable template auto-reload in prod, and allow toggling debug via env
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 60 * 60 * 24 * 7  # 7 days
app.config['TEMPLATES_AUTO_RELOAD'] = False
app.config['JSON_SORT_KEYS'] = False
app.config['DEBUG'] = os.environ.get("FLASK_DEBUG", "0") == "1"

# Enable gzip/br compression for faster responses over the network
Compress(app)

# Inicializa e migra o banco de dados para garantir que o schema está atualizado
database.iniciar_db()
database.migrar_db()
# Garante usuários básicos (admin e vendedor) caso não existam
try:
    database.ensure_usuarios_basicos()
except Exception as e:
    print(f"Aviso: falha ao garantir usuários básicos: {e}")
# Inicializa categorias financeiras padrão
try:
    database.inicializar_categorias_padrao()
except Exception as e:
    print(f"Aviso: falha ao inicializar categorias padrão: {e}")

# Caminhos absolutos para evitar problemas de diretório de trabalho
STATIC_FOLDER_ABS = os.path.join(app.root_path, 'static')
UPLOAD_FOLDER = os.path.join(STATIC_FOLDER_ABS, 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Logging em arquivo desabilitado a pedido do usuário
# Caso queira reativar no futuro, reintroduza um FileHandler aqui.

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Helper para salvar arquivo com nome único evitando sobrescrita
def save_unique(file_storage, field_name: str = "file", prefix: str | None = None) -> str:
    """
    Salva um arquivo em `UPLOAD_FOLDER` usando um nome único no formato:
    [prefix_]field_YYYYMMDD_HHMMSS_UUID8.ext

    Retorna apenas o nome do arquivo salvo (sem caminho).
    """
    fname = secure_filename(file_storage.filename)
    base, ext = os.path.splitext(fname)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    uniq = uuid.uuid4().hex[:8]
    parts = [p for p in [prefix, field_name, ts, uniq] if p]
    safe_name = f"{'_'.join(parts)}{ext.lower()}"
    dest = os.path.join(app.config['UPLOAD_FOLDER'], safe_name)
    file_storage.save(dest)
    return safe_name

# Gera modelos PDF básicos em static/ se não existirem
def ensure_model_docs():
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import A4
        import datetime
        docs = [
            ("GARANTIA.pdf", "Modelo de Garantia", [
                "Preencha com os dados da moto e do cliente.",
                "Este é um modelo base gerado automaticamente."
            ]),
            ("PROCURACAO.pdf", "PROCURAÇÃO", [
                "Pelo presente instrumento particular de procuração,",
                "Eu:",
                "CPF:",
                "ENDEREÇO:",
                "CEP:",
                "Nomeia e constitui-se bastante procurado HENRIQUE NASCIMENTO BITENCOURT CPF 396.894.918-81 Residente RODOVIA SALVADOR DE LEONE 2030 CEP 06853-000 a quem concedo os mais amplos, gerais e iluminados poderes a fim de que possa defender os direitos e interesses do (a) OUTORGANTE perante as repartições públicas em geral.",
                "Federais, Estaduais, Municipais, Autarquias, Oficiais de Registro Civil ou tabelionatos de notas, SPTrans, despachante, companhias de seguro, notadamente repartições de trânsito em geral, DETRAN/ CONTRAN/ CIRETRAN/ DENATRAN, DTP e demais órgãos autorizados de trânsito em qualquer cidade do território nacional, podendo solicitar 2ª via de CRV e CRLV, assinar/endossar transferências (DUT – Documento Único de Transferência), autorizar e acompanhar vistorias, efetuar pagamentos, receber pagamentos, receber os valores referente à venda do veículo seja à vista ou financiada, formular requerimentos, interpor recursos, reclamar, desistir, solicitar, cópias de processos, firmar declaração de venda, além de ter acesso a documentos de qualquer natureza, referente exclusivamente ao VEÍCULO descrito abaixo.",
                "Cláusula de Responsabilidade por Débitos Anteriores",
                "Declaro que qualquer débito existente antes da venda, como multas, são de minha inteira responsabilidade.",
                "Caso venham a existir débitos e eu não regularize os mesmos, autorizo expressamente que meu nome seja negativado em órgãos de proteção ao crédito (SPC, SERASA, etc.), conforme já acordado neste documento.",
                "",
                "MARCA/MODELO:",
                "ANO/MODELO:",
                "COR:",
                "PLACA:",
                "RENAVAM:",
                "CHASSI:",
                "Nos termos da Portaria Detran/SP nº 1680, cap II, art 8, Parágrafo VI.",
                "",
                "_________________________________________     Assinar e reconhecer firma por autenticidade",
            ]),
        ]
        for nome, titulo, linhas in docs:
            caminho = os.path.join(STATIC_FOLDER_ABS, nome)
            # Sempre (re)gerar o PDF do modelo para refletir atualizações de conteúdo
            c = canvas.Canvas(caminho, pagesize=A4)
            width, height = A4
            c.setFont("Helvetica-Bold", 18)
            c.drawString(72, height - 72, titulo)
            c.setFont("Helvetica", 11)
            y = height - 110
            for ln in linhas:
                c.drawString(72, y, ln)
                y -= 18
            c.setFont("Helvetica-Oblique", 9)
            c.drawString(72, 36, f"Gerado automaticamente em {datetime.date.today().isoformat()}")
            c.showPage()
            c.save()
    except Exception as e:
        print(f"Não foi possível gerar modelos PDF: {e}")

ensure_model_docs()

# Função global para checar existência de arquivo na pasta de uploads
app.jinja_env.globals['file_exists'] = lambda filename: bool(filename) and os.path.exists(os.path.join(UPLOAD_FOLDER, filename))

# Helper para obter a URL correta do arquivo (procura em static/uploads e fallback para static)
from flask import url_for
def _file_url(filename: str):
    if not filename:
        return None
    # Normaliza separadores e remove espaços extras
    p = str(filename).strip().replace('\\', '/')

    # Caso já venha como 'static/...'
    if 'static/' in p:
        rel = p.split('static/', 1)[1]
        full = os.path.join(STATIC_FOLDER_ABS, rel)
        if os.path.exists(full):
            return url_for('static', filename=rel)

    # Caso venha como 'uploads/...'
    if 'uploads/' in p:
        rel = p.split('uploads/', 1)[1]
        full = os.path.join(UPLOAD_FOLDER, rel)
        if os.path.exists(full):
            return url_for('static', filename=f'uploads/{rel}')

    # Tenta com apenas o nome do arquivo
    base = os.path.basename(p)
    if not base:
        return None
    # Se o valor parece não ser um arquivo (sem extensão) ou parece uma data, não gerar URL
    try:
        from re import match
        # Sem ponto na string => provavelmente não é arquivo
        if '.' not in base:
            return None
        # Padrão de data yyyy-mm-dd
        if match(r"^\d{4}-\d{2}-\d{2}$", base):
            return None
    except Exception:
        pass
    caminho_uploads = os.path.join(UPLOAD_FOLDER, base)
    if os.path.exists(caminho_uploads):
        return url_for('static', filename=f'uploads/{base}')
    caminho_static = os.path.join(STATIC_FOLDER_ABS, base)
    if os.path.exists(caminho_static):
        return url_for('static', filename=base)
    # Sem arquivo correspondente: não gerar URL inválida
    return None

app.jinja_env.globals['file_url'] = _file_url

@app.template_filter("br_moeda")
def br_moeda(valor):
    try:
        if valor is None:
            valor = 0
        return f"R$ {float(valor):,.2f}".replace(",", "v").replace(".", ",").replace("v", ".")
    except Exception:
        return "R$ 0,00"

@app.template_filter("br_km")
def br_km(valor):
    try:
        if valor is None:
            valor = 0
        return f"{float(valor):,.0f} km".replace(",", ".")
    except Exception:
        return "0 km"

@app.template_filter("is_image")
def is_image(filename):
    try:
        if not filename:
            return False
        name = str(filename).lower()
        return name.endswith((".png", ".jpg", ".jpeg", ".gif", ".webp"))
    except Exception:
        return False

# ROTAS DE DOWNLOAD DE MODELOS PDF
@app.route("/download/garantia")
def download_garantia():
    caminho = os.path.join(STATIC_FOLDER_ABS, "GARANTIA.pdf")
    if not os.path.exists(caminho):
        return redirect("/cadastro_moto")
    return send_file(caminho, as_attachment=True, download_name="GARANTIA.pdf")

@app.route("/download_procuracao")
def download_procuracao():
    caminho = os.path.join(STATIC_FOLDER_ABS, "PROCURACAO.pdf")
    if not os.path.exists(caminho):
        return redirect("/cadastro_moto")
    return send_file(caminho, as_attachment=True, download_name="PROCURACAO.pdf")

# Procuração dinâmica por moto
@app.route("/download_procuracao/<int:moto_id>")
def download_procuracao_moto(moto_id: int):
    if "usuario" not in session:
        return redirect("/")
    try:
        caminho_pdf = database.gerar_pdf_procuracao(moto_id)
        if caminho_pdf and os.path.exists(caminho_pdf):
            return send_file(caminho_pdf, as_attachment=True, download_name=f"procuracao_moto_{moto_id}.pdf")
        else:
            print(f"Procuração não encontrada/gerada para moto {moto_id}: {caminho_pdf}")
            return redirect("/listar_motos")
    except Exception as e:
        print(f"Erro ao gerar/baixar procuração da moto {moto_id}: {e}")
        return redirect("/listar_motos")

# Gerar Garantia dinâmica por moto (pós-venda)
@app.route("/gerar_garantia/<int:moto_id>")
def gerar_garantia_moto(moto_id: int):
    if "usuario" not in session or session.get("tipo") not in ("admin", "vendedor"):
        return redirect("/")
    try:
        caminho_pdf = database.gerar_pdf_garantia(moto_id)
        if caminho_pdf and os.path.exists(caminho_pdf):
            return send_file(caminho_pdf, as_attachment=True, download_name=f"garantia_moto_{moto_id}.pdf")
        else:
            flash("Não foi possível gerar a garantia. Verifique os dados da moto e do comprador.", "danger")
            return redirect(request.referrer or "/motos_vendidas")
    except Exception as e:
        flash(f"Erro ao gerar garantia: {e}", "danger")
        return redirect(request.referrer or "/motos_vendidas")

# LOGIN
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        usuario = request.form["usuario"]
        senha = request.form["senha"]
        tipo = database.verificar_login(usuario, senha)
        if tipo:
            session["usuario"] = usuario
            session["tipo"] = tipo
            return redirect("/menu")
        return render_template("login.html", erro=True)
    return render_template("login.html", erro=False)

@app.route("/sair")
def sair():
    session.clear()
    return redirect("/")

@app.route("/menu")
def menu():
    if "usuario" not in session:
        return redirect("/")

    if session["tipo"] == "admin":
        # Coleta os dados para o dashboard apenas para admin
        stats_estoque = database.get_stats_estoque()
        stats_vendas = database.get_stats_vendas_mes()
        
        dashboard_data = {
            'motos_disponiveis': stats_estoque[0],
            'valor_estoque': stats_estoque[1],
            'vendas_mes_qtd': stats_vendas[0],
            'vendas_mes_valor': stats_vendas[1]
        }
        return render_template("menu_admin.html", usuario=session["usuario"], dashboard=dashboard_data)
    else:  # Vendedor
        # Vendedor não tem acesso ao dashboard
        return render_template("menu_vendedor.html", usuario=session["usuario"])

# MOTOS
@app.route("/cadastro_moto", methods=["GET", "POST"])
def cadastro_moto():
    if "usuario" not in session or session["tipo"] not in ["admin", "vendedor"]:
        return redirect("/")
    if request.method == "POST":
        preco_br = request.form["preco"].replace(".", "").replace(",", ".")
        dados = {
            "marca": request.form["marca"],
            "modelo": request.form["modelo"],
            "ano": int(request.form["ano"]),
            "cor": request.form["cor"],
            "km": int(request.form["km"].replace(".", "")),
            "preco": float(request.form["preco"].replace(".", "").replace(",", ".")),
            "placa": request.form["placa"],
            "combustivel": request.form["combustivel"],
            # Respeitar o status enviado no formulário (padrão: disponivel)
            "status": (request.form.get("status") or "disponivel"),
            "data_cadastro": datetime.now().strftime("%Y-%m-%d"),
            "hora_cadastro": datetime.now().strftime("%H:%M:%S"),
            "nome_cliente": request.form.get("nome_cliente", ""),
            "cpf_cliente": request.form.get("cpf_cliente", ""),
            "rua_cliente": request.form.get("rua_cliente", ""),
            "cep_cliente": request.form.get("cep_cliente", ""),
            "celular_cliente": request.form.get("celular_cliente", ""),
            "referencia": request.form.get("referencia", ""),
            "celular_referencia": request.form.get("celular_referencia", ""),
            "debitos": request.form.get("debitos", ""),
            "observacoes": request.form.get("observacoes", ""),
            "renavam": request.form.get("renavam", ""),
            "chassi": request.form.get("chassi", ""),
            "doc_moto": None,
            "documento_fornecedor": None,
            "comprovante_residencia": None
        }

        # Prevenir duplicidade por PLACA (normalizada)
        try:
            if database.existe_moto_com_placa(dados["placa"]):
                flash('Já existe uma moto cadastrada com esta placa. Verifique antes de continuar.', 'danger')
                return redirect('/cadastro_moto')
        except Exception:
            pass

        # Processar uploads de documentos
        for campo_form in ['doc_moto', 'documento_fornecedor', 'documento_extra']:
            file = request.files.get(campo_form)
            if file and file.filename:
                db_campo = 'comprovante_residencia' if campo_form == 'documento_extra' else campo_form
                saved_name = save_unique(file, field_name=db_campo)
                dados[db_campo] = saved_name

        try:
            # 1. Cadastrar a moto no banco para obter o ID
            moto_id = database.cadastrar_moto(dados)

            # 2. Salvar a foto da moto usando o ID obtido
            foto = request.files.get('foto_moto')
            if foto and foto.filename:
                try:
                    fname = secure_filename(foto.filename)
                    _, ext = os.path.splitext(fname)
                    if ext.lower() in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
                        foto_name = f"foto_moto_{moto_id}{ext.lower()}"
                        foto_path = os.path.join(app.config['UPLOAD_FOLDER'], foto_name)
                        foto.save(foto_path)
                    else:
                        flash('Formato de imagem não suportado. Use JPG, PNG, GIF ou WEBP.', 'warning')
                except Exception as e:
                    app.logger.warning(f"Falha ao salvar foto da moto {moto_id}: {e}")
            
            # 3. Gerar procuração
            try:
                database.gerar_pdf_procuracao(moto_id)
            except Exception as e:
                app.logger.warning(f"Falha ao gerar procuração para moto {moto_id}: {e}")

            flash('Moto cadastrada com sucesso!', 'success')
            return redirect('/cadastro_moto')

        except Exception as e:
            app.logger.error(f"Erro ao cadastrar a moto: {e}")
            flash(f'Erro ao cadastrar a moto: {e}', 'danger')
            return redirect('/cadastro_moto')
    return render_template("cadastro_moto.html")

@app.route("/listar_motos")
def listar_motos():
    if "usuario" not in session:
        return redirect("/")
    filtros = {
        "marca_modelo": request.args.get("marca_modelo", ""),
        "placa": request.args.get("placa", ""),
        "renavam": request.args.get("renavam", ""),
        "combustivel": request.args.get("combustivel", ""),
        "ano_min": request.args.get("ano_min", ""),
        "ano_max": request.args.get("ano_max", ""),
        "km_min": request.args.get("km_min", ""),
        "km_max": request.args.get("km_max", ""),
        "preco_min": request.args.get("preco_min", ""),
        "preco_max": request.args.get("preco_max", ""),
        "status": request.args.get("status", ""),
        # deduplica por placa dentro do mesmo status para permitir exibir 'disponível' e 'consignado' juntos
        "dedup_por_status": True,
    }
    # Quando o usuário deixa Status em branco, mostrar estoque (disponível + consignado)
    if not filtros["status"]:
        filtros["estoque_apenas"] = True
    lista = database.filtrar_motos_completo(filtros)
    # Filtro por mês de CADASTRO (apenas estoque: não vendidas) opcional: periodo=YYYY-MM
    periodo = request.args.get('periodo', '').strip()
    if periodo:
        def matches_period_estoque(moto_row):
            # Índices segundo SELECT em database.filtrar_motos_completo
            # 0:id, 9:status, 15:data_cadastro
            st = (moto_row[9] or '').lower()
            if st == 'vendida':
                return False
            dc = str(moto_row[15] or '')
            if not dc:
                return False
            try:
                # data_cadastro pode estar como DD/MM/YYYY
                if '/' in dc:
                    partes = dc.split('/')
                    ym = f"{partes[2]}-{partes[1]}"
                elif '-' in dc and dc[4] == '-':
                    ym = dc[:7]
                else:
                    return False
                return ym == periodo
            except Exception:
                return False
        lista = [row for row in lista if matches_period_estoque(row)]
    # Buscar preço de venda (preco_final) mais recente por moto
    sale_prices = {}
    try:
        conn = database.get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT v.moto_id, v.preco_final
            FROM vendas v
            INNER JOIN (
                SELECT moto_id, MAX(id) AS max_id
                FROM vendas
                GROUP BY moto_id
            ) ult ON ult.moto_id = v.moto_id AND ult.max_id = v.id
            WHERE v.preco_final IS NOT NULL
            """
        )
        for moto_id, preco_final in cursor.fetchall():
            sale_prices[moto_id] = float(preco_final)
        # Também carregar anexos da última venda (CNH, Garantia assinada, Endereço)
        anexos_venda = {}
        cursor.execute(
            """
            SELECT v.moto_id, v.cnh_path, v.garantia_path, v.endereco_path
            FROM vendas v
            INNER JOIN (
                SELECT moto_id, MAX(id) AS max_id
                FROM vendas
                GROUP BY moto_id
            ) ult ON ult.moto_id = v.moto_id AND ult.max_id = v.id
            WHERE v.cnh_path IS NOT NULL OR v.garantia_path IS NOT NULL OR v.endereco_path IS NOT NULL
            """
        )
        for moto_id, cnh_p, gar_p, end_p in cursor.fetchall():
            anexos_venda[moto_id] = {
                'cnh': _file_url(cnh_p) if cnh_p else None,
                'garantia': _file_url(gar_p) if gar_p else None,
                'endereco': _file_url(end_p) if end_p else None,
            }
        conn.close()
    except Exception as e:
        print(f"Aviso: falha ao carregar preços de venda: {e}")
    # Mapear links de Folha de Exibição, Procuração e Foto por moto (Garantia NÃO deve aparecer na listagem)
    exibicao_urls = {}
    procuracao_urls = {}
    foto_urls = {}
    try:
        base_static = os.path.join(os.path.dirname(database.__file__), "static")
        for row in lista:
            moto_id = row[0]
            pdf_path = os.path.join(base_static, f"exibicao_moto_{moto_id}.pdf")
            if os.path.exists(pdf_path):
                exibicao_urls[moto_id] = url_for('static', filename=os.path.basename(pdf_path))
            # Sempre usar rota dinâmica para garantir dados atualizados
            try:
                procuracao_urls[moto_id] = url_for('download_procuracao_moto', moto_id=moto_id)
            except Exception:
                pass
            # Foto: procurar por extensões conhecidas
            for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
                p = os.path.join(app.config['UPLOAD_FOLDER'], f"foto_moto_{moto_id}{ext}")
                if os.path.exists(p):
                    foto_urls[moto_id] = url_for('static', filename=f"uploads/{os.path.basename(p)}")
                    break
    except Exception:
        pass
    return render_template(
        "listar_motos.html",
        motos=lista,
        filtros=filtros,
        periodo=periodo,
        exibicao_urls=exibicao_urls,
        procuracao_urls=procuracao_urls,
        foto_urls=foto_urls,
        sale_prices=sale_prices,
        anexos_venda=anexos_venda if 'anexos_venda' in locals() else {},
    )

@app.route("/motos_vendidas")
def motos_vendidas():
    if "usuario" not in session:
        return redirect("/")
    # Filtra apenas motos vendidas
    filtros = {
        "marca_modelo": request.args.get("marca_modelo", ""),
        "placa": request.args.get("placa", ""),
        "renavam": request.args.get("renavam", ""),
        "combustivel": request.args.get("combustivel", ""),
        "ano_min": request.args.get("ano_min", ""),
        "ano_max": request.args.get("ano_max", ""),
        "km_min": request.args.get("km_min", ""),
        "km_max": request.args.get("km_max", ""),
        "preco_min": request.args.get("preco_min", ""),
        "preco_max": request.args.get("preco_max", ""),
        "status": "vendida",
        "dedup_placa": True,
    }
    lista = database.filtrar_motos_completo(filtros)
    # Buscar preço de venda (preco_final) mais recente por moto e anexos (CNH, Garantia assinada, Endereço)
    sale_prices = {}
    sale_dates = {}
    anexos_venda = {}
    try:
        conn = database.get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT v.moto_id, v.preco_final, v.data
            FROM vendas v
            INNER JOIN (
                SELECT moto_id, MAX(id) AS max_id
                FROM vendas
                GROUP BY moto_id
            ) ult ON ult.moto_id = v.moto_id AND ult.max_id = v.id
            """
        )
        for moto_id, preco_final, data_venda in cursor.fetchall():
            if preco_final is not None:
                sale_prices[moto_id] = float(preco_final)
            # Guardar data (string como salva no banco)
            sale_dates[moto_id] = data_venda
        cursor.execute(
            """
            SELECT v.moto_id, v.cnh_path, v.garantia_path, v.endereco_path
            FROM vendas v
            INNER JOIN (
                SELECT moto_id, MAX(id) AS max_id
                FROM vendas
                GROUP BY moto_id
            ) ult ON ult.moto_id = v.moto_id AND ult.max_id = v.id
            WHERE v.cnh_path IS NOT NULL OR v.garantia_path IS NOT NULL OR v.endereco_path IS NOT NULL
            """
        )
        for moto_id, cnh_p, gar_p, end_p in cursor.fetchall():
            anexos_venda[moto_id] = {
                'cnh': _file_url(cnh_p) if cnh_p else None,
                'garantia': _file_url(gar_p) if gar_p else None,
                'endereco': _file_url(end_p) if end_p else None,
            }
        conn.close()
    except Exception as e:
        print(f"Aviso: falha ao carregar dados de vendas para motos vendidas: {e}")

    # Filtro opcional por mês (YYYY-MM) da data de saída
    periodo = request.args.get('periodo', '').strip()
    if periodo:
        def match_period(row):
            mid = row[0]
            dv = str(sale_dates.get(mid, '') or '')
            if not dv:
                return False
            try:
                if '-' in dv and dv[4] == '-':
                    ym = dv[:7]
                elif '/' in dv:
                    partes = dv.split(' ')[0].split('/')
                    ym = f"{partes[2]}-{partes[1]}"
                else:
                    return False
                return ym == periodo
            except Exception:
                return False
        lista = [row for row in lista if match_period(row)]

    # Mapear links de Procuração e Foto por moto (Garantia NÃO deve aparecer na listagem)
    procuracao_urls = {}
    foto_urls = {}
    try:
        base_static = os.path.join(os.path.dirname(database.__file__), "static")
        for row in lista:
            moto_id = row[0]
            # Sempre usar rota dinâmica para garantir dados atualizados
            try:
                procuracao_urls[moto_id] = url_for('download_procuracao_moto', moto_id=moto_id)
            except Exception:
                pass
            # Foto: procurar por extensões conhecidas
            for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
                p = os.path.join(app.config['UPLOAD_FOLDER'], f"foto_moto_{moto_id}{ext}")
                if os.path.exists(p):
                    foto_urls[moto_id] = url_for('static', filename=f"uploads/{os.path.basename(p)}")
                    break
    except Exception:
        pass

    return render_template(
        "motos_vendidas.html",
        motos=lista,
        filtros=filtros,
        procuracao_urls=procuracao_urls,
        foto_urls=foto_urls,
        sale_prices=sale_prices,
        sale_dates=sale_dates,
        anexos_venda=anexos_venda,
        lucros_por_mes=_calcular_lucros_por_mes(lista, sale_prices, sale_dates),
    )

def _calcular_lucros_por_mes(lista_motos, sale_prices, sale_dates):
    """
    Calcula lucros por mês (YYYY-MM) com base no preço de venda mais recente (sale_prices)
    menos o preço cadastrado (coluna 6 da lista) e agrupa pela data da venda em sale_dates.
    Retorna um dicionário { 'YYYY-MM': total_lucro_float } ordenado por mês.
    """
    try:
        # Agrupar somatórios
        somas = {}
        for row in lista_motos:
            try:
                moto_id = row[0]
                preco_base = float(row[6] or 0)
                pv = sale_prices.get(moto_id)
                if pv is None:
                    continue
                lucro = float(pv) - preco_base
                data_venda = str(sale_dates.get(moto_id) or '')
                if not data_venda:
                    continue
                # Normalizar para YYYY-MM
                ym = None
                if '-' in data_venda and len(data_venda) >= 7:
                    ym = data_venda[:7]
                elif '/' in data_venda:
                    try:
                        apenas_data = data_venda.split(' ')[0]
                        d, m, a = apenas_data.split('/')
                        ym = f"{a}-{m}"
                    except Exception:
                        ym = None
                if not ym:
                    continue
                somas[ym] = somas.get(ym, 0.0) + lucro
            except Exception:
                continue
        # Ordenar pelo mês
        return dict(sorted(somas.items()))
    except Exception:
        return {}
@app.route("/editar_moto/<int:id>", methods=["GET", "POST"])
def editar_moto(id):
    if "usuario" not in session or session["tipo"] not in ["admin", "vendedor"]:
        return redirect("/")
    moto = database.buscar_moto(id)
    if not moto:
        return redirect("/listar_motos")
    if request.method == "POST":
        preco_br = request.form["preco"].replace(".", "").replace(",", ".")
        km_br = request.form["km"].replace(".", "").replace(",", ".")
        # Normaliza data/hora: string vazia -> None (NULL no MySQL)
        data_cadastro_raw = request.form.get("data_cadastro", "").strip()
        hora_cadastro_raw = request.form.get("hora_cadastro", "").strip()
        data_cadastro_val = data_cadastro_raw or None
        hora_cadastro_val = hora_cadastro_raw or None
        # Tratar possíveis valores longos em campos VARCHAR
        cel_ref_raw = request.form.get("celular_referencia")
        if cel_ref_raw is not None:
            cel_ref_raw = cel_ref_raw[:255]

        dados = {
            "marca": request.form["marca"],
            "modelo": request.form["modelo"],
            "ano": int(request.form["ano"]),
            "cor": request.form["cor"],
            "km": round(float(km_br), 2),
            "preco": round(float(preco_br), 2),
            "placa": request.form["placa"],
            "combustivel": request.form["combustivel"],
            "status": request.form["status"],
            "renavam": request.form.get("renavam"),
            "chassi": request.form.get("chassi"),
            # Inicializar campos de arquivos como None para manter alinhamento e usar COALESCE no UPDATE
            "doc_moto": None,
            "documento_fornecedor": None,
            "comprovante_residencia": None,
            "data_cadastro": data_cadastro_val,
            "hora_cadastro": hora_cadastro_val,
            "nome_cliente": request.form.get("nome_cliente"),
            "cpf_cliente": request.form.get("cpf_cliente"),
            "rua_cliente": request.form.get("rua_cliente"),
            "cep_cliente": request.form.get("cep_cliente"),
            "celular_cliente": request.form.get("celular_cliente"),
            "referencia": request.form.get("referencia"),
            "celular_referencia": cel_ref_raw,
            "debitos": request.form.get("debitos"),
            # Observações: quando em branco, salvar como string vazia (não None)
            "observacoes": (request.form.get("observacoes") or "").strip(),
        }

        # Prevenir duplicidade de placa ao editar (ignora o próprio ID)
        try:
            if database.existe_moto_com_placa(dados["placa"], excluir_id=id):
                flash('Já existe outra moto com esta placa. Alteração não aplicada.', 'danger')
                return redirect(f"/editar_moto/{id}")
        except Exception:
            pass

        # Processar uploads de documentos, atualizando somente se um novo arquivo for enviado
        for campo_form in ['doc_moto', 'documento_fornecedor', 'documento_extra']:
            file = request.files.get(campo_form)
            if file and file.filename:
                db_campo = 'comprovante_residencia' if campo_form == 'documento_extra' else campo_form
                saved_name = save_unique(file, field_name=db_campo, prefix=f"moto{id}")
                dados[db_campo] = saved_name

        

        # Processar foto da moto (opcional)
        foto = request.files.get('foto_moto')
        if foto and foto.filename:
            fname = secure_filename(foto.filename)
            _, ext = os.path.splitext(fname)
            ext = (ext or '').lower()
            if ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
                foto_name = f"foto_moto_{id}{ext}"
                foto_path = os.path.join(app.config['UPLOAD_FOLDER'], foto_name)
                foto.save(foto_path)
            else:
                flash('Formato de imagem não suportado. Use JPG, PNG, GIF ou WEBP.', 'warning')

        # Efetivar atualização e redirecionar
        database.atualizar_moto(id, dados)
        return redirect("/listar_motos")
    return render_template("editar_moto.html", moto=moto)

@app.route("/excluir_moto/<int:id>")
def excluir_moto(id):
    if "usuario" not in session or session["tipo"] != "admin":
        return redirect("/")
    database.excluir_moto(id)
    return redirect("/listar_motos")

    return redirect("/")

@app.route("/listar_clientes")
def listar_clientes():
    if "usuario" not in session or session["tipo"] not in ["admin", "vendedor"]:
        return redirect("/")
    clientes = database.listar_clientes()
    return render_template("listar_clientes.html", clientes=clientes)

# VENDAS
@app.route("/registrar_venda", methods=["GET", "POST"])
def registrar_venda():
    if "usuario" not in session or session["tipo"] not in ["admin", "vendedor"]:
        return redirect("/")

    # Usar página independente (não dentro do menu com abas)
    tpl_registro = "registrar_venda.html"

    # Processa o registro da venda
    if request.method == "POST":
        moto_id = int(request.form["moto_id"])
        data = request.form["data"]
        # Preço final (opcional) em formato BRL
        preco_final_raw = request.form.get("preco_final", "").strip()
        preco_final_val = None
        if preco_final_raw:
            try:
                preco_final_val = float(preco_final_raw.replace("R$", "").replace(" ", "").replace(".", "").replace(",", "."))
            except Exception:
                preco_final_val = None
        # Atualiza dados do comprador (se informados) na moto
        nome_cli = request.form.get("nome_cliente", "").strip()
        cpf_cli = request.form.get("cpf_cliente", "").strip()
        rua_cli = request.form.get("rua_cliente", "").strip()
        cep_cli = request.form.get("cep_cliente", "").strip()
        try:
            database.atualizar_campos_comprador(
                moto_id,
                nome=nome_cli or None,
                cpf=cpf_cli or None,
                rua=rua_cli or None,
                cep=cep_cli or None,
            )
        except Exception as e:
            print(f"Aviso: não foi possível atualizar dados do comprador para a moto {moto_id}: {e}")
        # O cliente_id foi removido do sistema
        # Processar uploads (CNH, Garantia assinada, Comprovante de Endereço) - opcionais
        cnh_filename = None
        garantia_filename = None
        endereco_filename = None
        try:
            for campo, varname in [("cnh_file", "cnh_filename"), ("garantia_file", "garantia_filename"), ("endereco_file", "endereco_filename")]:
                f = request.files.get(campo)
                if f and f.filename:
                    fname = secure_filename(f.filename)
                    # prefixar com moto e timestamp para evitar conflitos
                    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                    base, ext = os.path.splitext(fname)
                    safe_name = f"{campo}_{moto_id}_{ts}{ext.lower()}"
                    dest = os.path.join(app.config['UPLOAD_FOLDER'], safe_name)
                    f.save(dest)
                    if varname == "cnh_filename":
                        cnh_filename = safe_name
                    elif varname == "garantia_filename":
                        garantia_filename = safe_name
                    elif varname == "endereco_filename":
                        endereco_filename = safe_name
        except Exception as e:
            print(f"Falha ao salvar anexos da venda da moto {moto_id}: {e}")

        resultado = database.registrar_venda(
            moto_id,
            session["usuario"],
            data,
            preco_final=preco_final_val,
            cnh_path=cnh_filename,
            garantia_path=garantia_filename,
            endereco_path=endereco_filename,
        )
        if resultado:
            # resultado é o venda_id; usar para gerar garantia com data da venda
            pdf_path = database.gerar_pdf_garantia(moto_id, venda_id=resultado)
            pdf_url = url_for('static', filename=os.path.basename(pdf_path)) if pdf_path else None
            # gerar Procuração e montar URL
            procuracao_path = database.gerar_pdf_procuracao(moto_id, venda_id=resultado)
            procuracao_url = url_for('static', filename=os.path.basename(procuracao_path)) if procuracao_path else None
            # Montar URLs de visualização/impressão dos anexos (se existirem)
            cnh_url = _file_url(cnh_filename) if cnh_filename else None
            garantia_anexada_url = _file_url(garantia_filename) if garantia_filename else None
            endereco_url = _file_url(endereco_filename) if endereco_filename else None
            return render_template(
                tpl_registro,
                sucesso=True,
                venda_id=resultado,
                moto_id=moto_id,
                pdf_garantia_url=pdf_url,
                pdf_procuracao_url=procuracao_url,
                cnh_url=cnh_url,
                garantia_anexada_url=garantia_anexada_url,
                endereco_url=endereco_url,
                filtros={},
            )
        else:
            return render_template(
                tpl_registro,
                sucesso=False,
                filtros={},
            )

    # Exibe a página de busca e seleção de motos
    filtros = {
        "marca_modelo": request.args.get("marca_modelo", ""),
        "placa": request.args.get("placa", ""),
        "renavam": request.args.get("renavam", ""),
        "combustivel": request.args.get("combustivel", ""),
        "ano_min": request.args.get("ano_min", ""),
        "ano_max": request.args.get("ano_max", ""),
        "km_min": request.args.get("km_min", ""),
        "km_max": request.args.get("km_max", ""),
        "preco_min": request.args.get("preco_min", ""),
        "preco_max": request.args.get("preco_max", ""),
        # Mostrar motos em estoque (disponível/disponivel + consignado) para poder vender consignadas também
        "status": "",
        "estoque_apenas": True,
        "dedup_por_status": True,
    }
    # Lista estoque (disponíveis + consignado); aplica filtros adicionais se informados
    lista_motos = database.filtrar_motos_completo(filtros)
    
    return render_template(
        tpl_registro,
        motos=lista_motos,
        filtros=filtros,
        sucesso=None,
    )

@app.route("/recibo_venda/<int:id>")
def recibo_venda(id):
    if "usuario" not in session:
        return redirect("/")
    dados = database.detalhes_venda(id)
    if not dados:
        return redirect("/relatorio")
    # Tentar descobrir PDFs já gerados para esta venda/moto
    pdf_garantia_url = None
    try:
        moto_id = dados[0]
        base_static = os.path.join(os.path.dirname(database.__file__), "static")
        gar = os.path.join(base_static, f"garantia_moto_{moto_id}.pdf")
        if os.path.exists(gar):
            pdf_garantia_url = url_for('static', filename=os.path.basename(gar))
    except Exception:
        pass
    # Importante: Não expor link de Procuração aqui; Procuração só deve aparecer na listagem de motos.
    return render_template("recibo_venda.html", dados=dados, pdf_garantia_url=pdf_garantia_url)

@app.route("/download_recibo/<int:id>")
def download_recibo(id):
    # Nota: id aqui é o moto_id, mas precisamos usar a função original para manter compatibilidade
    try:
        caminho_pdf = database.gerar_pdf_recibo(id)
        if caminho_pdf and os.path.exists(caminho_pdf):
            return send_file(caminho_pdf, as_attachment=True, download_name=f"recibo_moto_{id}.pdf")
        else:
            # Se o arquivo não foi criado ou não existe, redireciona com erro
            print(f"Arquivo PDF não encontrado: {caminho_pdf}")
            return redirect("/relatorio?erro=pdf_nao_encontrado")
    except Exception as e:
        print(f"Erro ao gerar/baixar recibo: {e}")
        return redirect("/relatorio?erro=erro_pdf")

## Folha de Exibição removida a pedido do usuário (rotas desativadas)

@app.route("/download_recibo_venda/<int:venda_id>")
def download_recibo_venda(venda_id):
    try:
        caminho_arquivo = database.gerar_pdf_recibo_por_venda_id(venda_id)
        if caminho_arquivo and os.path.exists(caminho_arquivo):
            # Verificar se é PDF ou HTML
            if caminho_arquivo.endswith('.pdf'):
                nome_download = f"recibo_venda_{venda_id}.pdf"
                return send_file(caminho_arquivo, as_attachment=True, download_name=nome_download)
            elif caminho_arquivo.endswith('.html'):
                # Para HTML, abrir em nova aba ao invés de download
                return send_file(caminho_arquivo, mimetype='text/html')
        else:
            print(f"Arquivo não encontrado: {caminho_arquivo}")
            return redirect("/relatorio?erro=arquivo_nao_encontrado")
    except Exception as e:
        print(f"Erro ao baixar recibo da venda {venda_id}: {e}")
        return redirect("/relatorio?erro=erro_download")

# RELATÓRIO
@app.route("/relatorio")
def relatorio():
    if "usuario" not in session:
        return redirect("/")
    estoque, vendas, resumo = database.gerar_relatorio()
    return render_template("relatorio.html", estoque=estoque, vendas=vendas, resumo=resumo)

@app.route("/redefinir_senha_usuario/<int:usuario_id>", methods=["POST"])
def redefinir_senha_usuario(usuario_id):
    if 'usuario' not in session or session.get('tipo') != 'admin':
        return redirect('/')
    nova_senha = request.form.get('nova_senha')
    if not nova_senha or len(nova_senha) < 4:
        flash('Senha inválida. Mínimo 4 caracteres.', 'danger')
        return redirect('/gerenciar_usuarios')
    database.atualizar_senha_por_id(usuario_id, nova_senha)
    flash('Senha atualizada com sucesso.', 'success')
    return redirect('/gerenciar_usuarios')

# Excluir usuário (somente admin)
@app.route('/excluir_usuario/<int:usuario_id>', methods=['POST'])
def excluir_usuario(usuario_id):
    if 'usuario' not in session or session.get('tipo') != 'admin':
        return redirect('/')
    ok = database.excluir_usuario(usuario_id)
    if ok:
        flash('Usuário excluído com sucesso.', 'success')
    else:
        flash('Não foi possível excluir este usuário (pode ser admin ou não existe).', 'danger')
    return redirect('/gerenciar_usuarios')

# USUÁRIOS
@app.route('/gerenciar_usuarios', methods=['GET', 'POST'])
def gerenciar_usuarios():
    if 'usuario' not in session or session.get('tipo') != 'admin':
        return redirect('/')

    if request.method == 'POST':
        if 'criar' in request.form:
            nome = request.form['nome']
            senha = request.form['senha']
            email = request.form['email']
            tipo = request.form.get('tipo', 'vendedor')
            if not database.criar_usuario(nome, senha, email, tipo):
                flash('Nome de usuário ou e-mail já existem.', 'danger')
        elif 'excluir' in request.form:
            usuario_id = request.form['usuario_id']
            database.excluir_usuario(usuario_id)
        return redirect('/gerenciar_usuarios')

    usuarios = database.get_todos_usuarios()
    return render_template('gerenciar_usuarios.html', usuarios=usuarios)

## Seção de despesas removida a pedido do usuário: rotas /despesas e /download_despesas excluídas

@app.route("/dashboard_financeiro")
def dashboard_financeiro():
    if "usuario" not in session or session["tipo"] != "admin":
        return redirect("/")
    # A funcionalidade de despesas foi removida; manter o dashboard exibindo mensagem vazia
    resumo = {}
    return render_template("dashboard_financeiro.html", resumo=resumo)

## Rota /despesas_por_ano removida a pedido do usuário

@app.route("/controle_financeiro")
def controle_financeiro():
    if "usuario" not in session or session["tipo"] != "admin":
        return redirect("/")
    
    # Inicializar categorias padrão se necessário
    database.inicializar_categorias_padrao()
    
    # Filtro por mês (input type=month -> YYYY-MM)
    periodo = request.args.get('periodo', '')
    if periodo and len(periodo) == 7 and '-' in periodo:
        receitas = database.ver_receitas_financeiras_filtrado(periodo)
        gastos = database.ver_gastos_financeiros_filtrado(periodo)
    else:
        receitas = database.ver_receitas_financeiras()
        gastos = database.ver_gastos_financeiros()
    
    # Dados para os gráficos a partir das listas selecionadas
    receita_total = sum(float(r[3]) for r in receitas) if receitas else 0.0
    gastos_total = sum(float(g[3]) for g in gastos) if gastos else 0.0
    saldo_total = receita_total - gastos_total
    valores_bar = [receita_total, gastos_total, saldo_total]
    
    # Pizza com gastos por categoria (recalcular daqui)
    from collections import defaultdict
    soma_cat = defaultdict(float)
    for g in gastos:
        soma_cat[str(g[1])] += float(g[3])
    categorias_labels = list(soma_cat.keys())
    categorias_valores = [soma_cat[k] for k in categorias_labels]
    valores_pizza = [categorias_labels, categorias_valores]
    
    # Calcular percentagem restante
    receita_total, gastos_total, saldo_total = valores_bar
    percentagem = ((receita_total - gastos_total) / receita_total * 100) if receita_total > 0 else 0
    percentagem = max(0, percentagem)
    
    # Dados da tabela (combinar receitas e gastos) - usar listas já filtradas
    dados_tabela = []
    for r in receitas:
        dados_tabela.append({
            'id': r[0],
            'tipo': 'receita',
            'categoria': r[1],
            'data': r[2],
            'valor': r[3],
            'valor_formatado': f"R$ {float(r[3]):,.2f}".replace(",", "v").replace(".", ",").replace("v", ".")
        })
    
    for g in gastos:
        dados_tabela.append({
            'id': g[0],
            'tipo': 'gasto',
            'categoria': g[1],
            'data': g[2],
            'valor': g[3],
            'valor_formatado': f"R$ {float(g[3]):,.2f}".replace(",", "v").replace(".", ",").replace("v", ".")
        })
    
    # Ordenar por ID decrescente
    dados_tabela.sort(key=lambda x: x['id'], reverse=True)
    
    # Categorias para o formulário
    categorias = database.ver_categorias_financeiras()
    
    return render_template('controle_financeiro.html',
                         valores_bar=valores_bar,
                         valores_pizza=valores_pizza,
                         percentagem=percentagem,
                         dados_tabela=dados_tabela,
                         categorias=categorias,
                         periodo=periodo)

@app.route("/inserir_categoria_financeira", methods=['POST'])
def inserir_categoria_financeira():
    if "usuario" not in session or session["tipo"] != "admin":
        return redirect("/")
    
    nome = request.form.get('nome_categoria')
    if nome:
        sucesso = database.inserir_categoria_financeira(nome)
        if sucesso:
            flash('Categoria inserida com sucesso!', 'success')
        else:
            flash('Categoria já existe!', 'danger')
    else:
        flash('Nome da categoria é obrigatório', 'danger')
    
    return redirect('/controle_financeiro')

@app.route("/deletar_categoria_financeira/<int:categoria_id>", methods=['POST'])
def deletar_categoria_financeira(categoria_id):
    if "usuario" not in session or session["tipo"] != "admin":
        return redirect("/")
    try:
        ok = database.deletar_categoria_financeira(categoria_id)
        if ok:
            flash('Categoria excluída com sucesso.', 'success')
        else:
            flash('Categoria não encontrada.', 'danger')
    except Exception as e:
        flash(f'Erro ao excluir categoria: {e}', 'danger')
    return redirect('/controle_financeiro')

# Upload de Garantia pós-venda (admin e vendedor)
@app.route("/upload_garantia/<int:moto_id>", methods=['POST'])
def upload_garantia(moto_id):
    if "usuario" not in session or session.get("tipo") not in ("admin", "vendedor"):
        return redirect("/")
    file = request.files.get('garantia')
    if not file or not file.filename:
        flash('Selecione um arquivo de garantia para enviar.', 'danger')
        return redirect(request.referrer or '/motos_vendidas')
    try:
        saved_name = save_unique(file, field_name='garantia', prefix=f"moto{moto_id}")
        ok = database.atualizar_garantia_venda(moto_id, saved_name)
        if ok:
            flash('Garantia anexada com sucesso!', 'success')
        else:
            flash('Não foi possível localizar a venda desta moto para anexar a garantia.', 'danger')
    except Exception as e:
        flash(f'Erro ao anexar garantia: {e}', 'danger')
    return redirect(request.referrer or '/motos_vendidas')

@app.route("/atualizar_preco_venda", methods=['POST'])
def atualizar_preco_venda():
    if "usuario" not in session or session.get("tipo") != "admin":
        return redirect("/")
    try:
        moto_id_raw = request.form.get('moto_id')
        preco_str = request.form.get('preco_final')
        if not moto_id_raw or preco_str is None:
            flash('Parâmetros inválidos para atualizar preço.', 'danger')
            return redirect(request.referrer or '/motos_vendidas')
        moto_id = int(moto_id_raw)
        # Normalizar valor "R$ 1.234,56" -> 1234.56
        preco_norm = None
        try:
            preco_norm = float(preco_str.replace('R$', '').replace(' ', '').replace('.', '').replace(',', '.'))
        except Exception:
            pass
        if preco_norm is None:
            flash('Valor inválido. Use o formato 1.234,56.', 'danger')
            return redirect(request.referrer or '/motos_vendidas')
        ok = database.atualizar_preco_venda_ultima(moto_id, preco_norm)
        if ok:
            flash('Preço de venda atualizado com sucesso.', 'success')
        else:
            flash('Não foi possível atualizar o preço (sem venda registrada?).', 'warning')
    except Exception as e:
        flash(f'Erro ao atualizar preço de venda: {e}', 'danger')
    return redirect(request.referrer or '/motos_vendidas')

@app.route("/atualizar_data_venda", methods=['POST'])
def atualizar_data_venda():
    if "usuario" not in session or session.get("tipo") not in ("admin", "vendedor"):
        return redirect("/")
    try:
        moto_id_raw = request.form.get('moto_id')
        data_venda = request.form.get('data_venda')  # esperado como YYYY-MM-DD (input type=date)
        hora_venda = request.form.get('hora_venda')  # esperado como HH:MM (input type=time)
        if not moto_id_raw or not data_venda:
            flash('Parâmetros inválidos para atualizar data.', 'danger')
            return redirect(request.referrer or '/motos_vendidas')
        moto_id = int(moto_id_raw)
        # Sanitização simples do formato
        data_venda = data_venda.strip()
        if hora_venda and hora_venda.strip():
            # Monta 'YYYY-MM-DD HH:MM'
            data_venda = f"{data_venda} {hora_venda.strip()[:5]}"
        ok = database.atualizar_data_venda_ultima(moto_id, data_venda)
        if ok:
            flash('Data da venda atualizada com sucesso.', 'success')
        else:
            flash('Não foi possível atualizar a data (verifique se há venda registrada).', 'warning')
    except Exception as e:
        flash(f'Erro ao atualizar data da venda: {e}', 'danger')
    return redirect(request.referrer or '/motos_vendidas')

@app.route("/editar_item_financeiro/<tipo>/<int:item_id>", methods=['POST'])
def editar_item_financeiro(tipo, item_id):
    if "usuario" not in session or session["tipo"] != "admin":
        return redirect("/")
    try:
        categoria = request.form.get('categoria')
        data_str = request.form.get('data')  # esperado no formato DD/MM/YYYY
        valor_str = request.form.get('valor')

        # Normalizar valor "R$ 1.234,56" -> 1234.56
        valor = None
        if valor_str is not None and valor_str.strip() != "":
            try:
                valor = float(valor_str.replace('R$', '').replace(' ', '').replace('.', '').replace(',', '.'))
            except Exception:
                valor = None

        # Data: aceitar já em DD/MM/YYYY; se vier yyyy-mm-dd (de input date), converter
        if data_str and '-' in data_str and '/' not in data_str:
            try:
                from datetime import datetime
                data_str = datetime.strptime(data_str, '%Y-%m-%d').strftime('%d/%m/%Y')
            except Exception:
                pass

        if tipo == 'receita':
            database.atualizar_receita_financeira(item_id, data=data_str, valor=valor, categoria=categoria)
            flash('Receita atualizada com sucesso!', 'success')
        elif tipo == 'gasto':
            database.atualizar_gasto_financeiro(item_id, categoria=categoria, data=data_str, valor=valor)
            flash('Gasto atualizado com sucesso!', 'success')
        else:
            flash('Tipo inválido para edição.', 'danger')
    except Exception as e:
        flash(f'Erro ao atualizar item: {e}', 'danger')
    return redirect('/controle_financeiro')

@app.route("/inserir_receita_financeira", methods=['POST'])
def inserir_receita_financeira():
    if "usuario" not in session or session["tipo"] != "admin":
        return redirect("/")
    
    data = request.form.get('data_receita')
    valor_str = request.form.get('valor_receita')
    
    if data and valor_str:
        try:
            # Converter data de YYYY-MM-DD para DD/MM/YYYY
            from datetime import datetime
            data_convertida = datetime.strptime(data, '%Y-%m-%d').strftime('%d/%m/%Y')
            
            # Extrair valor numérico
            valor_limpo = valor_str.replace('R$', '').replace('.', '').replace(',', '.').strip()
            valor = float(valor_limpo)
            
            database.inserir_receita_financeira('Entrada', data_convertida, valor)
            flash('Receita inserida com sucesso!', 'success')
        except Exception as e:
            flash(f'Erro ao inserir receita: {e}', 'danger')
    else:
        flash('Todos os campos são obrigatórios', 'danger')
    
    return redirect('/controle_financeiro')

@app.route("/inserir_gasto_financeiro", methods=['POST'])
def inserir_gasto_financeiro():
    if "usuario" not in session or session["tipo"] != "admin":
        return redirect("/")
    
    categoria = request.form.get('categoria_gasto')
    data = request.form.get('data_gasto')
    valor_str = request.form.get('valor_gasto')
    
    if categoria and data and valor_str:
        try:
            # Converter data de YYYY-MM-DD para DD/MM/YYYY
            from datetime import datetime
            data_convertida = datetime.strptime(data, '%Y-%m-%d').strftime('%d/%m/%Y')
            
            # Extrair valor numérico
            valor_limpo = valor_str.replace('R$', '').replace('.', '').replace(',', '.').strip()
            valor = float(valor_limpo)
            
            database.inserir_gasto_financeiro(categoria, data_convertida, valor)
            flash('Gasto inserido com sucesso!', 'success')
        except Exception as e:
            flash(f'Erro ao inserir gasto: {e}', 'danger')
    else:
        flash('Todos os campos são obrigatórios', 'danger')
    
    return redirect('/controle_financeiro')

@app.route("/deletar_item_financeiro/<tipo>/<int:item_id>")
def deletar_item_financeiro(tipo, item_id):
    if "usuario" not in session or session["tipo"] != "admin":
        return redirect("/")
    
    try:
        if tipo == 'receita':
            database.deletar_receita_financeira(item_id)
            flash('Receita deletada com sucesso!', 'success')
        elif tipo == 'gasto':
            database.deletar_gasto_financeiro(item_id)
            flash('Gasto deletado com sucesso!', 'success')
        else:
            flash('Tipo de item inválido', 'danger')
    except Exception as e:
        flash(f'Erro ao deletar item: {e}', 'danger')
    
    return redirect('/controle_financeiro')

# VENDAS POR VENDEDOR COM FILTRO E GRÁFICO
@app.route("/vendas_por_vendedor")
def vendas_por_vendedor():
    if "usuario" not in session:
        return redirect("/")
    
    data_inicio = request.args.get("data_inicio")
    data_fim = request.args.get("data_fim")
    ordenar = request.args.get("ordenar_por", "total_vendas")

    conn = database.get_db_connection()
    cursor = conn.cursor()

    # Query com JOIN para calcular receita total
    query = """
        SELECT v.vendedor,
               COUNT(m.id) AS total_vendas,
               COALESCE(SUM(COALESCE(v.preco_final, m.preco)), 0) AS receita_total
        FROM vendas v
        INNER JOIN motos m ON v.moto_id = m.id
        WHERE 1=1
    """
    params = []

    if data_inicio:
        query += " AND v.data >= %s"
        params.append(data_inicio)
    if data_fim:
        query += " AND v.data <= %s"
        params.append(data_fim)

    # Ajustar ordenação baseada no parâmetro
    if ordenar == "total_receita":
        query += f" GROUP BY v.vendedor ORDER BY receita_total DESC"
    else:
        query += f" GROUP BY v.vendedor ORDER BY total_vendas DESC"
    cursor.execute(query, params)
    vendas = cursor.fetchall()
    conn.close()

    return render_template("vendas_por_vendedor.html", vendas=vendas)

# EXPORTAÇÃO PARA EXCEL
@app.route("/exportar_vendas_excel")
def exportar_vendas_excel():
    import pandas as pd
    conn = database.get_db_connection()
    df = pd.read_sql(
        """
        SELECT v.vendedor,
               COUNT(m.id) AS total_vendas,
               COALESCE(SUM(COALESCE(v.preco_final, m.preco)), 0) AS receita_total
        FROM vendas v
        INNER JOIN motos m ON v.moto_id = m.id
        GROUP BY v.vendedor
        ORDER BY total_vendas DESC
        """,
        conn,
    )
    conn.close()

    pasta = os.path.join(app.root_path, "static", "exports")
    os.makedirs(pasta, exist_ok=True)
    caminho = os.path.join(pasta, "vendas_por_vendedor.xlsx")
    df.to_excel(caminho, index=False)

    return send_file(caminho, as_attachment=True, download_name="vendas_por_vendedor.xlsx")

# Exportação de Motos para Excel (admin)
@app.route("/exportar_motos_excel")
def exportar_motos_excel():
    if "usuario" not in session or session.get("tipo") != "admin":
        return redirect("/")
    import pandas as pd
    conn = database.get_db_connection()
    df = pd.read_sql(
        """
        SELECT id, marca, modelo, ano, cor, km, preco, placa, combustivel, status
        FROM motos
        ORDER BY id DESC
        """,
        conn,
    )
    conn.close()
    pasta = os.path.join(app.root_path, "static", "exports")
    os.makedirs(pasta, exist_ok=True)
    caminho = os.path.join(pasta, "motos.xlsx")
    df.to_excel(caminho, index=False)
    return send_file(caminho, as_attachment=True, download_name="motos.xlsx")

@app.errorhandler(404)
def not_found(e):
    return render_template("erro_404.html"), 404

# INICIALIZAÇÃO DO SISTEMA
if __name__ == "__main__":
    database.iniciar_db()
    app.run(debug=True, port=8080)