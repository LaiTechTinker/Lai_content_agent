from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False, index=True)
    password_hash: Mapped[str | None] = mapped_column(String(255))
    name: Mapped[str | None] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default="CURRENT_TIMESTAMP")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default="CURRENT_TIMESTAMP")

    ideas: Mapped[list["ContentIdea"]] = relationship(back_populates="user")
    content: Mapped[list["GeneratedContent"]] = relationship(back_populates="user")
    documents: Mapped[list["Document"]] = relationship(back_populates="user")
    social_accounts: Mapped[list["SocialAccount"]] = relationship(back_populates="user")
    oauth_states: Mapped[list["OAuthState"]] = relationship(back_populates="user")
    publications: Mapped[list["ContentPublication"]] = relationship(back_populates="user")
    workflow_sessions: Mapped[list["WorkflowSession"]] = relationship(back_populates="user")


class ContentIdea(Base):
    __tablename__ = "content_ideas"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    topic: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    angle: Mapped[str | None] = mapped_column(Text)
    platform: Mapped[str | None] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default="CURRENT_TIMESTAMP")
    user: Mapped[User | None] = relationship(back_populates="ideas")


class GeneratedContent(Base):
    __tablename__ = "generated_content"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    idea_id: Mapped[int | None] = mapped_column(ForeignKey("content_ideas.id", ondelete="SET NULL"), index=True)
    platform: Mapped[str] = mapped_column(String(50), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    quality_score: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str | None] = mapped_column(String(50), server_default="draft", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default="CURRENT_TIMESTAMP")
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    user: Mapped[User | None] = relationship(back_populates="content")
    versions: Mapped[list["ContentVersion"]] = relationship(back_populates="content_record", cascade="all, delete-orphan")
    media: Mapped[list["ContentMedia"]] = relationship(back_populates="content", cascade="all, delete-orphan")
    publications: Mapped[list["ContentPublication"]] = relationship(back_populates="content")


class ContentVersion(Base):
    __tablename__ = "content_versions"
    __table_args__ = (UniqueConstraint("content_id", "version_number", name="uq_content_version_number"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    content_id: Mapped[int] = mapped_column(ForeignKey("generated_content.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    evaluation: Mapped[dict | None] = mapped_column(JSON)
    metadata_json: Mapped[dict | None] = mapped_column("metadata", JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default="CURRENT_TIMESTAMP")
    content_record: Mapped[GeneratedContent] = relationship(back_populates="versions")


class Document(Base):
    __tablename__ = "documents"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    filename: Mapped[str] = mapped_column(Text, nullable=False)
    file_type: Mapped[str | None] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default="CURRENT_TIMESTAMP")
    user: Mapped[User | None] = relationship(back_populates="documents")
    chunks: Mapped[list["DocumentChunk"]] = relationship(back_populates="document", cascade="all, delete-orphan")


class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default="CURRENT_TIMESTAMP")
    document: Mapped[Document] = relationship(back_populates="chunks")


class ContentMedia(Base):
    __tablename__ = "content_media"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    content_id: Mapped[int] = mapped_column(ForeignKey("generated_content.id", ondelete="CASCADE"), nullable=False, index=True)
    media_type: Mapped[str] = mapped_column(String(50), nullable=False)
    media_url: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str | None] = mapped_column(String(50), index=True)
    attempt_count: Mapped[int | None] = mapped_column(Integer)
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default="CURRENT_TIMESTAMP")
    content: Mapped[GeneratedContent] = relationship(back_populates="media")


class SocialAccount(Base):
    __tablename__ = "social_accounts"
    __table_args__ = (UniqueConstraint("user_id", "platform", name="uq_social_account_user_platform"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    platform: Mapped[str] = mapped_column(String(50), nullable=False)
    account_id: Mapped[str | None] = mapped_column(String(255))
    account_name: Mapped[str | None] = mapped_column(String(255))
    access_token: Mapped[str] = mapped_column(Text, nullable=False)
    refresh_token: Mapped[str | None] = mapped_column(Text)
    token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default="CURRENT_TIMESTAMP")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default="CURRENT_TIMESTAMP")
    connected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default="CURRENT_TIMESTAMP")
    user: Mapped[User | None] = relationship(back_populates="social_accounts")


class OAuthState(Base):
    __tablename__ = "oauth_states"
    state: Mapped[str] = mapped_column(String(255), primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    platform: Mapped[str] = mapped_column(String(50), nullable=False)
    code_verifier: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default="CURRENT_TIMESTAMP")
    user: Mapped[User | None] = relationship(back_populates="oauth_states")


class ContentPublication(Base):
    __tablename__ = "content_publications"
    __table_args__ = (Index("ix_publication_user_created", "user_id", "created_at"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    content_id: Mapped[int] = mapped_column(ForeignKey("generated_content.id", ondelete="CASCADE"), nullable=False, index=True)
    platform: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    account_id: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(50), nullable=False, server_default="pending", index=True)
    platform_post_id: Mapped[str | None] = mapped_column(String(255))
    platform_post_url: Mapped[str | None] = mapped_column(Text)
    error_message: Mapped[str | None] = mapped_column(Text)
    media_ids: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default="CURRENT_TIMESTAMP")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default="CURRENT_TIMESTAMP")
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    user: Mapped[User | None] = relationship(back_populates="publications")
    content: Mapped[GeneratedContent] = relationship(back_populates="publications")


class WorkflowSession(Base):
    __tablename__ = "workflow_sessions"
    __table_args__ = (UniqueConstraint("thread_id", name="uq_workflow_session_thread_id"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    thread_id: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str | None] = mapped_column(String(50), index=True)
    current_stage: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default="CURRENT_TIMESTAMP")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default="CURRENT_TIMESTAMP")
    user: Mapped[User | None] = relationship(back_populates="workflow_sessions")


class RefreshSession(Base):
    __tablename__ = "refresh_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default="CURRENT_TIMESTAMP")
    user: Mapped[User] = relationship()