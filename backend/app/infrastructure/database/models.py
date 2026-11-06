import uuid
from datetime import datetime
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

EMBED_DIMS = 1024


class Base(DeclarativeBase):
    pass


class BookModel(Base):
    __tablename__ = "books"
    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True, autoincrement=False)
    osis: Mapped[str] = mapped_column(String(10), unique=True)
    step_code: Mapped[str] = mapped_column(String(10), unique=True)
    pt_name: Mapped[str] = mapped_column(String(40))
    abbrev: Mapped[str] = mapped_column(String(10))
    testament: Mapped[str] = mapped_column(String(2))
    chapters: Mapped[int] = mapped_column(Integer)


class TranslationModel(Base):
    __tablename__ = "translations"
    code: Mapped[str] = mapped_column(String(12), primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    indexed: Mapped[bool] = mapped_column(Boolean, default=False)


class VerseModel(Base):
    __tablename__ = "verses"
    __table_args__ = (
        UniqueConstraint("translation_code", "book_id", "chapter", "verse"),
        Index("ix_verses_tsv", "tsv", postgresql_using="gin"),
        Index("ix_verses_norm_ref", "book_id", "chapter", "verse"),
    )
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    translation_code: Mapped[str] = mapped_column(ForeignKey("translations.code", ondelete="CASCADE"))
    book_id: Mapped[int] = mapped_column(ForeignKey("books.id"))
    chapter: Mapped[int] = mapped_column(Integer)
    verse: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)
    text_norm: Mapped[str] = mapped_column(Text)
    tsv: Mapped[Any] = mapped_column(TSVECTOR)


class ChapterAlignmentModel(Base):
    __tablename__ = "chapter_alignment"
    translation_code: Mapped[str] = mapped_column(ForeignKey("translations.code", ondelete="CASCADE"), primary_key=True)
    book_id: Mapped[int] = mapped_column(ForeignKey("books.id"), primary_key=True)
    chapter: Mapped[int] = mapped_column(Integer, primary_key=True)
    ok: Mapped[bool] = mapped_column(Boolean)
    reason: Mapped[str | None] = mapped_column(String(40))


class PassageModel(Base):
    __tablename__ = "passages"
    __table_args__ = (
        Index("ix_passages_tsv", "tsv", postgresql_using="gin"),
        Index(
            "ix_passages_embedding",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
        UniqueConstraint("translation_code", "book_id", "chapter", "verse_start", "verse_end"),
    )
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    translation_code: Mapped[str] = mapped_column(ForeignKey("translations.code", ondelete="CASCADE"))
    book_id: Mapped[int] = mapped_column(ForeignKey("books.id"))
    chapter: Mapped[int] = mapped_column(Integer)
    verse_start: Mapped[int] = mapped_column(Integer)
    verse_end: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)
    tsv: Mapped[Any] = mapped_column(TSVECTOR)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBED_DIMS), nullable=True)


class OriginalWordModel(Base):
    __tablename__ = "original_words"
    __table_args__ = (
        Index("ix_original_words_ref", "book_id", "chapter", "verse"),
        Index("ix_original_words_strong", "strong"),
        CheckConstraint("language IN ('heb','arc','grc')", name="ck_original_words_language"),
    )
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    book_id: Mapped[int] = mapped_column(ForeignKey("books.id"))
    chapter: Mapped[int] = mapped_column(Integer)
    verse: Mapped[int] = mapped_column(Integer)
    position: Mapped[int] = mapped_column(Integer)
    surface: Mapped[str] = mapped_column(Text)
    transliteration: Mapped[str] = mapped_column(Text)
    gloss_en: Mapped[str] = mapped_column(Text)
    strong: Mapped[str] = mapped_column(String(12))
    morphology: Mapped[str] = mapped_column(String(40))
    language: Mapped[str] = mapped_column(String(3))
    editions: Mapped[str | None] = mapped_column(Text)


class LexiconModel(Base):
    __tablename__ = "lexicon"
    strong: Mapped[str] = mapped_column(String(12), primary_key=True)
    lemma: Mapped[str] = mapped_column(Text)
    transliteration: Mapped[str] = mapped_column(Text)
    gloss: Mapped[str] = mapped_column(Text)
    definition: Mapped[str] = mapped_column(Text)


class CrossReferenceModel(Base):
    __tablename__ = "cross_references"
    __table_args__ = (Index("ix_cross_references_from", "from_book", "from_chapter", "from_verse"),)
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    from_book: Mapped[int] = mapped_column(SmallInteger)
    from_chapter: Mapped[int] = mapped_column(Integer)
    from_verse: Mapped[int] = mapped_column(Integer)
    to_book: Mapped[int] = mapped_column(SmallInteger)
    to_chapter_start: Mapped[int] = mapped_column(Integer)
    to_verse_start: Mapped[int] = mapped_column(Integer)
    to_chapter_end: Mapped[int] = mapped_column(Integer)
    to_verse_end: Mapped[int] = mapped_column(Integer)
    votes: Mapped[int] = mapped_column(Integer)


class ConversationModel(Base):
    __tablename__ = "conversations"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(120), default="Nova conversa")
    agent_session_id: Mapped[str | None] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class MessageModel(Base):
    __tablename__ = "messages"
    __table_args__ = (UniqueConstraint("conversation_id", "seq"),)
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    conversation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("conversations.id", ondelete="CASCADE"))
    seq: Mapped[int] = mapped_column(Integer)
    role: Mapped[str] = mapped_column(String(12))
    text: Mapped[str | None] = mapped_column(Text)
    display_segments: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class MemoryModel(Base):
    __tablename__ = "memories"
    path: Mapped[str] = mapped_column(String(80), primary_key=True)
    content: Mapped[str] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class IngestionCheckpointModel(Base):
    __tablename__ = "ingestion_checkpoints"
    step: Mapped[str] = mapped_column(String(80), primary_key=True)
    detail: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    done_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
