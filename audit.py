
from __future__ import annotations

import asyncio
import logging
from datetime import timedelta

import discord

from config_store import ConfigStore


log = logging.getLogger("central_inteligencia.audit")

CATEGORY_LABELS = {
    "canais": "Canais",
    "cargos": "Cargos",
    "permissoes": "Permissões",
    "membros": "Membros",
    "moderacao": "Moderação",
    "servidor": "Servidor",
}


def display(value):
    if value is None:
        return "Nenhum"

    if isinstance(value, discord.abc.User):
        return f"{value} (`{value.id}`)"

    if hasattr(value, "mention"):
        return f"{value.mention} (`{value.id}`)"

    return str(value)


def make_embed(title, description=None):
    embed = discord.Embed(
        title=title,
        description=description,
        color=discord.Colour.dark_blue(),
        timestamp=discord.utils.utcnow(),
    )
    embed.set_footer(text="Sistema de Inteligência | CAÇA-RATOS")
    return embed


def add_field(embed, name, value):
    value = str(value)
    if len(value) > 1024:
        value = value[:1021] + "..."
    embed.add_field(name=name, value=value, inline=False)


def add_target(embed, target):
    add_field(embed, "Alvo", display(target))


def permission_changes(before, after):
    changes = []

    before_values = dict(before)
    after_values = dict(after)

    for name, new_value in after_values.items():
        old_value = before_values.get(name)

        if old_value == new_value:
            continue

        old_text = "Permitida" if old_value else "Não permitida"
        new_text = "Permitida" if new_value else "Não permitida"

        changes.append(
            f"**{name}:** {old_text} → {new_text}"
        )

    return changes


async def find_audit_entry(
    guild,
    action,
    target_id=None,
):
    if not guild.me or not guild.me.guild_permissions.view_audit_log:
        return None

    for attempt in range(3):
        try:
            async for entry in guild.audit_logs(
                limit=10,
                action=action,
            ):
                created = entry.created_at
                age = discord.utils.utcnow() - created

                if age > timedelta(seconds=30):
                    continue

                if target_id is not None:
                    entry_target = getattr(entry, "target", None)
                    if getattr(entry_target, "id", None) != target_id:
                        continue

                return entry

        except discord.Forbidden:
            log.warning(
                "Sem permissão para consultar auditoria em %s.",
                guild.id,
            )
            return None

        except discord.HTTPException:
            log.exception("Erro ao consultar auditoria.")

        if attempt < 2:
            await asyncio.sleep(1)

    return None


async def add_responsible(embed, guild, action, target_id=None):
    entry = await find_audit_entry(
        guild,
        action,
        target_id,
    )

    if entry:
        add_field(embed, "Responsável", display(entry.user))
        if entry.reason:
            add_field(embed, "Motivo", entry.reason)
        return entry

    add_field(
        embed,
        "Responsável",
        "Não identificado pela auditoria do Discord.",
    )
    return None


class AuditLogger:
    def __init__(self, bot, store: ConfigStore):
        self.bot = bot
        self.store = store

    async def send(self, guild, category, embed):
        try:
            config = await self.store.get(guild.id)

            if not config["categories"].get(category, True):
                return

            channel_id = config.get("log_channel_id")
            if not channel_id:
                return

            channel = guild.get_channel(channel_id)

            if channel is None:
                channel = await self.bot.fetch_channel(channel_id)

            if not isinstance(channel, discord.TextChannel):
                return

            await channel.send(embed=embed)

        except discord.NotFound:
            log.warning("Canal de auditoria não encontrado.")

        except discord.Forbidden:
            log.warning("Sem permissão para enviar registros.")

        except discord.HTTPException:
            log.exception("Falha ao enviar registro de auditoria.")

    async def log_channel_create(self, channel):
        embed = make_embed("Canal criado")
        add_target(embed, channel)

        await add_responsible(
            embed,
            channel.guild,
            discord.AuditLogAction.channel_create,
            channel.id,
        )

        await self.send(channel.guild, "canais", embed)

    async def log_channel_delete(self, channel):
        embed = make_embed("Canal excluído")
        add_target(embed, channel)

        await add_responsible(
            embed,
            channel.guild,
            discord.AuditLogAction.channel_delete,
            channel.id,
        )

        await self.send(channel.guild, "canais", embed)

    async def log_channel_update(self, before, after):
        changes = []

        for attribute, label in (
            ("name", "Nome"),
            ("topic", "Descrição"),
            ("nsfw", "Conteúdo NSFW"),
            ("slowmode_delay", "Modo lento"),
            ("category_id", "Categoria"),
        ):
            old = getattr(before, attribute, None)
            new = getattr(after, attribute, None)

            if old != new:
                changes.append(
                    f"**{label}:** `{old}` → `{new}`"
                )

        if changes:
            embed = make_embed(
                "Canal alterado",
                "\n".join(changes),
            )
            add_target(embed, after)

            await add_responsible(
                embed,
                after.guild,
                discord.AuditLogAction.channel_update,
                after.id,
            )

            await self.send(after.guild, "canais", embed)

        if before.overwrites != after.overwrites:
            embed = make_embed(
                "Permissões do canal alteradas",
                "As permissões de acesso deste canal foram modificadas.",
            )
            add_target(embed, after)

            await add_responsible(
                embed,
                after.guild,
                discord.AuditLogAction.overwrite_update,
                after.id,
            )

            await self.send(after.guild, "permissoes", embed)

    async def log_role_create(self, role):
        embed = make_embed("Cargo criado")
        add_target(embed, role)

        await add_responsible(
            embed,
            role.guild,
            discord.AuditLogAction.role_create,
            role.id,
        )

        await self.send(role.guild, "cargos", embed)

    async def log_role_delete(self, role):
        embed = make_embed("Cargo excluído")
        add_target(embed, role)

        await add_responsible(
            embed,
            role.guild,
            discord.AuditLogAction.role_delete,
            role.id,
        )

        await self.send(role.guild, "cargos", embed)

    async def log_role_update(self, before, after):
        changes = []

        for attribute, label in (
            ("name", "Nome"),
            ("colour", "Cor"),
            ("hoist", "Exibição separada"),
            ("mentionable", "Mencionável"),
            ("permissions", "Permissões"),
        ):
            old = getattr(before, attribute)
            new = getattr(after, attribute)

            if old != new:
                if attribute == "permissions":
                    differences = permission_changes(old, new)
                    changes.extend(differences)
                else:
                    changes.append(
                        f"**{label}:** `{old}` → `{new}`"
                    )

        if not changes:
            return

        embed = make_embed(
            "Cargo alterado",
            "\n".join(changes),
        )
        add_target(embed, after)

        await add_responsible(
            embed,
            after.guild,
            discord.AuditLogAction.role_update,
            after.id,
        )

        category = (
            "permissoes"
            if before.permissions != after.permissions
            else "cargos"
        )

        await self.send(after.guild, category, embed)

    async def log_member_update(self, before, after):
        changes = []

        if before.nick != after.nick:
            changes.append(
                f"**Apelido:** `{before.nick}` → `{after.nick}`"
            )

        old_roles = {role.id for role in before.roles}
        new_roles = {role.id for role in after.roles}

        added = [
            role.mention
            for role in after.roles
            if role.id not in old_roles
        ]

        removed = [
            role.mention
            for role in before.roles
            if role.id not in new_roles
        ]

        if added:
            changes.append("**Cargos adicionados:** " + ", ".join(added))

        if removed:
            changes.append("**Cargos removidos:** " + ", ".join(removed))

        if before.timed_out_until != after.timed_out_until:
            changes.append(
                "**Tempo de timeout:** "
                f"`{before.timed_out_until}` → "
                f"`{after.timed_out_until}`"
            )

        if not changes:
            return

        embed = make_embed(
            "Membro atualizado",
            "\n".join(changes),
        )
        add_target(embed, after)

        if old_roles != new_roles:
            await add_responsible(
                embed,
                after.guild,
                discord.AuditLogAction.member_role_update,
                after.id,
            )

        await self.send(after.guild, "membros", embed)

    async def log_member_name_update(self, before, after):
        if before.name == after.name and before.global_name == after.global_name:
            return

        for guild in self.bot.guilds:
            member = guild.get_member(before.id)

            if member is None:
                continue

            embed = make_embed(
                "Nome de usuário alterado",
                f"**Antes:** `{before.name}`\n"
                f"**Depois:** `{after.name}`",
            )
            add_target(embed, member)

            await self.send(guild, "membros", embed)

    async def log_member_join(self, member):
        embed = make_embed(
            "Membro entrou no servidor",
            f"{member.mention} entrou no servidor.",
        )
        add_target(embed, member)

        await self.send(member.guild, "membros", embed)

    async def log_member_remove(self, member):
        entry = await find_audit_entry(
            member.guild,
            discord.AuditLogAction.kick,
            member.id,
        )

        if entry:
            embed = make_embed("Membro expulso")
            add_target(embed, member)
            add_field(embed, "Responsável", display(entry.user))

            if entry.reason:
                add_field(embed, "Motivo", entry.reason)
        else:
            embed = make_embed(
                "Membro saiu do servidor",
                f"{member} deixou o servidor.",
            )
            add_target(embed, member)

        await self.send(member.guild, "membros", embed)

    async def log_ban(self, guild, user):
        embed = make_embed("Membro banido")
        add_target(embed, user)

        await add_responsible(
            embed,
            guild,
            discord.AuditLogAction.ban,
            user.id,
        )

        await self.send(guild, "moderacao", embed)

    async def log_unban(self, guild, user):
        embed = make_embed("Banimento removido")
        add_target(embed, user)

        await add_responsible(
            embed,
            guild,
            discord.AuditLogAction.unban,
            user.id,
        )

        await self.send(guild, "moderacao", embed)

    async def log_guild_update(self, before, after):
        changes = []

        for attribute, label in (
            ("name", "Nome do servidor"),
            ("description", "Descrição"),
            ("verification_level", "Nível de verificação"),
            ("explicit_content_filter", "Filtro de conteúdo"),
            ("afk_timeout", "Tempo de ausência"),
        ):
            old = getattr(before, attribute, None)
            new = getattr(after, attribute, None)

            if old != new:
                changes.append(
                    f"**{label}:** `{old}` → `{new}`"
                )

        if not changes:
            return

        embed = make_embed(
            "Configurações do servidor alteradas",
            "\n".join(changes),
        )

        await add_responsible(
            embed,
            after,
            discord.AuditLogAction.guild_update,
            after.id,
        )

        await self.send(after, "servidor", embed)

