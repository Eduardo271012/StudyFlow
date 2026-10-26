from database import db


class SessaoEstudo(db.Model):
    __tablename__ = "sessoes_estudo"

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)
    inicio_em = db.Column(db.DateTime(timezone=True), nullable=False)
    fim_em = db.Column(db.DateTime(timezone=True), nullable=True)
    duracao_segundos = db.Column(db.Integer, default=0, nullable=False)
    status = db.Column(db.String(20), default="ativa", nullable=False)
    compartilhada = db.Column(db.Boolean, default=False, nullable=False)
