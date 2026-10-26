from datetime import datetime, timezone
from sqlalchemy import UniqueConstraint
from sqlalchemy.engine import default

from database import db

class ParticipanteTurma(db.Model):
    __tablename__ = 'participantes_turma'

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    turma_id = db.Column(db.Integer, db.ForeignKey('turmas.id'), nullable=False)
    papel = db.Column(db.String(20), default="aluno", nullable=False)
    entrou_em = db.Column(db.DateTime(timezone=True), default=lambda:datetime.now(timezone.utc), nullable=False)

    __table_args__ = (UniqueConstraint('usuario_id', 'turma_id', name='uq_usuario_turma'),)