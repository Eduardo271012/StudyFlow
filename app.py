from flask import Flask, render_template, request, flash, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
from database import configurar_banco, db
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from banco.tabela_usuario import Usuario
from banco.tabela_sessao_estudo import SessaoEstudo
from datetime import datetime, timedelta
import banco



def criar_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "chave-temporaria-do-studyflow"

    configurar_banco(app)
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = "login"

    @login_manager.user_loader
    def carregar_usuario(usuario_id):
        return db.session.get(Usuario, int(usuario_id))

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/cadastro", methods=["GET", "POST"])
    def cadastro():
        if request.method == "POST":
            nome = request.form.get("nome", "").strip()
            email = request.form.get("email", "").strip().lower()
            senha = request.form.get("senha", "")
            confirmar_senha = request.form.get("confirmar_senha", "")

            if not nome or not email or not senha or not confirmar_senha:
                flash("Preencha todos os campos.", "error")
                return redirect(url_for("cadastro"))

            if senha != confirmar_senha:
                flash("As senhas não são iguais.", "error")
                return redirect(url_for("cadastro"))

            usuario_existente = Usuario.query.filter_by(email=email).first()

            if usuario_existente:
                flash("Este e-mail já está cadastrado.", "error")
                return redirect(url_for("cadastro"))

            novo_usuario = Usuario(nome=nome, email=email, senha_hash=generate_password_hash(senha))

            db.session.add(novo_usuario)
            db.session.commit()
            flash("Conta criada com sucesso!.", "success")
            return redirect(url_for("cadastro"))

        return render_template("cadastro.html")



    @app.route("/login", methods=["GET", "POST"])
    def login():
        if current_user.is_authenticated:
            flash("Você já está conectado.", "sucesso")
            return redirect(url_for("index"))

        if request.method == "POST":
            email = request.form.get("email", "").strip().lower()
            senha = request.form.get("senha", "")

            usuario = Usuario.query.filter_by(email=email).first()

            if usuario and check_password_hash(usuario.senha_hash, senha):
                login_user(usuario)
                flash("Login realizado com sucesso!", "sucesso")
                return redirect(url_for("dashboard"))

            flash("E-mail ou senha incorretos.", "erro")
            return redirect(url_for("login"))

        return render_template("login.html")

    @app.route("/logout")
    @login_required
    def logout():
        logout_user()
        flash("Você saiu da sua conta.", "sucesso")
        return redirect(url_for("index"))

    @app.route("/dashboard", methods=["GET", "POST"])
    @login_required
    def dashboard():
        if request.method == "POST":
            acao = request.form.get("acao")

            if acao == "iniciar":
                try:
                    duracao = int(request.form.get("duracao", "25"))

                    if duracao not in [15, 25, 45, 60]:
                        raise ValueError

                except ValueError:
                    flash("Selecione uma duração válida.", "erro")
                    return redirect(url_for("dashboard"))

                session["inicio_foco"] = datetime.now().timestamp()
                session["duracao_foco"] = duracao * 60

                flash("Sessão de foco iniciada!", "sucesso")

            elif acao == "reiniciar":
                session.pop("inicio_foco", None)
                session.pop("duracao_foco", None)

                flash("Sessão de foco reiniciada.", "sucesso")

            return redirect(url_for("dashboard"))

        tempo_restante = 25 * 60

        if "inicio_foco" in session and "duracao_foco" in session:
            inicio = session["inicio_foco"]
            duracao_total = session["duracao_foco"]

            tempo_passado = datetime.now().timestamp() - inicio
            tempo_restante = max(0, int(duracao_total - tempo_passado))

        minutos = tempo_restante // 60
        segundos = tempo_restante % 60
        tempo_formatado = f"{minutos:02d}:{segundos:02d}"

        return render_template(
            "dashboard.html",
            tempo_formatado=tempo_formatado
        )

    @app.route("/historico")
    @login_required
    def historico():
        sessoes = SessaoEstudo.query.filter(
            SessaoEstudo.usuario_id == current_user.id,
            SessaoEstudo.status.in_(["concluida", "interrompida"])
        ).order_by(
            SessaoEstudo.inicio_em.desc()
        ).all()

        return render_template(
            "historico.html",
            sessoes=sessoes
        )

    @app.route("/historico/apagar/<int:sessao_id>", methods=["POST"])
    @login_required
    def apagar_sessao(sessao_id):
        sessao = SessaoEstudo.query.filter(
            SessaoEstudo.id == sessao_id,
            SessaoEstudo.usuario_id == current_user.id,
            SessaoEstudo.status.in_(["concluida", "interrompida"])
        ).first()

        if sessao is None:
            flash("Sessão não encontrada.", "erro")
            return redirect(url_for("historico"))

        db.session.delete(sessao)
        db.session.commit()

        flash("Sessão apagada com sucesso!", "sucesso")
        return redirect(url_for("historico"))

    @app.route("/foco/iniciar", methods=["POST"])
    @login_required
    def iniciar_sessao():
        # Procura uma sessão anterior que ficou ativa
        sessao_anterior = SessaoEstudo.query.filter_by(
            usuario_id=current_user.id,
            status="ativa"
        ).order_by(
            SessaoEstudo.inicio_em.desc()
        ).first()

        if sessao_anterior is not None:
            sessao_anterior.fim_em = datetime.now()
            sessao_anterior.status = "interrompida"

            # Não sabemos quanto tempo o usuário realmente estudou.
            # Por segurança, mantemos a duração já registrada.
            db.session.commit()

        # Cria a nova sessão
        nova_sessao = SessaoEstudo(
            usuario_id=current_user.id,
            inicio_em=datetime.now(),
            duracao_segundos=0,
            status="ativa",
            compartilhada=False
        )

        db.session.add(nova_sessao)
        db.session.commit()

        return {"sessao_id": nova_sessao.id}, 201

    @app.route("/foco/finalizar", methods=["POST"])
    @login_required
    def finalizar_sessao():
        dados = request.get_json(silent=True) or {}

        sessao_id = dados.get("sessao_id")
        duracao = dados.get("duracao_segundos")

        if sessao_id is None or duracao is None:
            return {"erro": "Dados da sessão não informados."}, 400

        try:
            sessao_id = int(sessao_id)
            duracao = int(duracao)
        except (TypeError, ValueError):
            return {"erro": "Dados inválidos."}, 400

        if duracao < 0:
            return {"erro": "A duração não pode ser negativa."}, 400

        sessao = SessaoEstudo.query.filter_by(
            id=sessao_id,
            usuario_id=current_user.id,
            status="ativa"
        ).first()

        if sessao is None:
            return {"erro": "Sessão não encontrada ou já finalizada."}, 404

        sessao.fim_em = datetime.now()
        sessao.duracao_segundos = duracao
        sessao.status = "concluida"

        db.session.commit()

        return {"mensagem": "Sessão concluída com sucesso."}, 200

    @app.route("/foco/interromper", methods=["POST"])
    @login_required
    def interromper_sessao():
        dados = request.get_json(silent=True) or {}

        sessao_id = dados.get("sessao_id")
        duracao = dados.get("duracao_segundos")

        if sessao_id is None or duracao is None:
            return {"erro": "Dados da sessão não informados."}, 400

        try:
            sessao_id = int(sessao_id)
            duracao = int(duracao)
        except (TypeError, ValueError):
            return {"erro": "Dados inválidos."}, 400

        if duracao < 0:
            return {"erro": "A duração não pode ser negativa."}, 400

        sessao = SessaoEstudo.query.filter_by(
            id=sessao_id,
            usuario_id=current_user.id,
            status="ativa"
        ).first()

        if sessao is None:
            return {"erro": "Sessão não encontrada ou já finalizada."}, 404

        sessao.fim_em = datetime.now()
        sessao.duracao_segundos = duracao
        sessao.status = "interrompida"

        db.session.commit()

        return {"mensagem": "Sessão interrompida com sucesso."}, 200

    return app


app = criar_app()


if __name__ == "__main__":
    app.run(debug=True)
