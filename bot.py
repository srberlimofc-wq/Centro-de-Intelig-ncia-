from __future__ import annotations

import asyncio
import logging
import os

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

from audit import AuditLogger, CATEGORY_LABELS
from config_store import ConfigStore

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

log = logging.getLogger("central_inteligencia")

FOOTER = "Sistema de Inteligência | CAÇA-RATOS"
AUTHOR = "C.I. — CENTRAL DE INTELIGÊNCIA"


class CentralInteligencia(commands.Bot):

    def __init__(self, store: ConfigStore):
        intents = discord.Intents.default()
        intents.guilds = True
        intents.members = True
        intents.moderation = True

        super().__init__(
            command_prefix=commands.when_mentioned,
            intents=intents,
        )

        self.store = store
        self.audit = AuditLogger(self, store)

    async def setup_hook(self):
        dev_guild = os.getenv("DEV_GUILD_ID", "").strip()

        if dev_guild:
            guild = discord.Object(id=int(dev_guild))
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            log.info("Comandos sincronizados no servidor de testes.")
        else:
            await self.tree.sync()
            log.info("Comandos globais sincronizados.")

    async def on_ready(self):
        log.info("CAÇA-RATOS conectado como %s", self.user)

    async def on_guild_channel_create(self, channel):
        await self.audit.log_channel_create(channel)

    async def on_guild_channel_delete(self, channel):
        await self.audit.log_channel_delete(channel)

    async def on_guild_channel_update(self, before, after):
        await self.audit.log_channel_update(before, after)

    async def on_guild_role_create(self, role):
        await self.audit.log_role_create(role)

    async def on_guild_role_delete(self, role):
        await self.audit.log_role_delete(role)

    async def on_guild_role_update(self, before, after):
        await self.audit.log_role_update(before, after)

    async def on_member_update(self, before, after):
        await self.audit.log_member_update(before, after)

    async def on_user_update(self, before, after):
        await self.audit.log_member_name_update(before, after)

    async def on_member_join(self, member):
        await self.audit.log_member_join(member)

    async def on_member_remove(self, member):
        await self.audit.log_member_remove(member)

    async def on_member_ban(self, guild, user):
        await self.audit.log_ban(guild, user)

    async def on_member_unban(self, guild, user):
        await self.audit.log_unban(guild, user)

    async def on_guild_update(self, before, after):
        await self.audit.log_guild_update(before, after)

    async def on_app_command_error(self, interaction, error):
        log.error(
            "Erro em comando de aplicação.",
            exc_info=error,
        )

        message = "Ocorreu um erro ao executar o comando."

        try:
            if interaction.response.is_done():
                await interaction.followup.send(
                    message,
                    ephemeral=True,
                )
            else:
                await interaction.response.send_message(
                    message,
                    ephemeral=True,
                )
        except discord.HTTPException:
            log.exception("Falha ao informar erro ao usuário.")


store = ConfigStore(
    os.getenv("CONFIG_PATH", "data/config.json")
)

bot = CentralInteligencia(store)


def is_authorized(interaction, config):
    if interaction.guild is None:
        return False

    if not isinstance(interaction.user, discord.Member):
        return False

    member = interaction.user

    if member.guild_permissions.administrator:
        return True

    role_id = config.get("admin_role_id")

    return bool(
        role_id
        and any(role.id == int(role_id) for role in member.roles)
    )


async def check_permission(interaction):
    config = await store.get(interaction.guild.id)

    if not is_authorized(interaction, config):
        await interaction.response.send_message(
            "Você não tem autorização para utilizar esta função.",
            ephemeral=True,
        )
        return None

    return config


# ==========================================
# COMANDO: /ci-avisos
# ==========================================

@bot.tree.command(
    name="ci-avisos",
    description="Publica um comunicado oficial da Central de Inteligência.",
)
@app_commands.describe(
    titulo="Título do comunicado",
    mensagem="Texto que será publicado",
    canal="Canal onde o comunicado será publicado",
)
async def ci_avisos(
    interaction: discord.Interaction,
    titulo: str,
    mensagem: str,
    canal: discord.TextChannel,
):
    if interaction.guild is None:
        await interaction.response.send_message(
            "Utilize este comando dentro do servidor.",
            ephemeral=True,
        )
        return

    config = await check_permission(interaction)

    if config is None:
        return

    if canal.guild.id != interaction.guild.id:
        await interaction.response.send_message(
            "Escolha um canal deste servidor.",
            ephemeral=True,
        )
        return

    if len(titulo) > 256 or len(mensagem) > 4000:
        await interaction.response.send_message(
            "O título deve ter até 256 caracteres e a mensagem até 4000.",
            ephemeral=True,
        )
        return

    permissions = canal.permissions_for(interaction.guild.me)

    if not permissions.send_messages or not permissions.embed_links:
        await interaction.response.send_message(
            "Preciso das permissões Enviar mensagens e Inserir links no canal.",
            ephemeral=True,
        )
        return

    embed = discord.Embed(
        title=titulo,
        description=mensagem,
        color=discord.Colour.dark_blue(),
        timestamp=discord.utils.utcnow(),
    )

    embed.set_author(name=AUTHOR)
    embed.set_footer(text=FOOTER)

    try:
        await canal.send(embed=embed)
    except discord.HTTPException:
        await interaction.response.send_message(
            "Não consegui publicar o comunicado.",
            ephemeral=True,
        )
        return

    await interaction.response.send_message(
        f"Comunicado publicado com sucesso em {canal.mention}.",
        ephemeral=True,
    )

    log.info(
        "Comunicado publicado por %s no servidor %s, canal %s.",
        interaction.user,
        interaction.guild.id,
        canal.id,
    )


# ==========================================
# COMANDO: /ci-auditoria
# ==========================================

@bot.tree.command(
    name="ci-auditoria",
    description="Configura e consulta o sistema de auditoria.",
)
@app_commands.choices(
    acao=[
        app_commands.Choice(name="Consultar configuração", value="status"),
        app_commands.Choice(name="Definir canal de registros", value="canal"),
        app_commands.Choice(name="Definir cargo autorizado", value="cargo"),
        app_commands.Choice(name="Ativar ou desativar categoria", value="categoria"),
    ],
    categoria=[
        app_commands.Choice(name="Canais", value="canais"),
        app_commands.Choice(name="Cargos", value="cargos"),
        app_commands.Choice(name="Permissões", value="permissoes"),
        app_commands.Choice(name="Membros", value="membros"),
        app_commands.Choice(name="Moderação", value="moderacao"),
        app_commands.Choice(name="Servidor", value="servidor"),
    ],
)
async def ci_auditoria(
    interaction: discord.Interaction,
    acao: app_commands.Choice[str],
    canal: discord.TextChannel | None = None,
    cargo: discord.Role | None = None,
    categoria: app_commands.Choice[str] | None = None,
    ativo: bool | None = None,
):
    if interaction.guild is None:
        await interaction.response.send_message(
            "Utilize este comando dentro do servidor.",
            ephemeral=True,
        )
        return

    config = await check_permission(interaction)

    if config is None:
        return

    if acao.value == "status":
        channel_id = config.get("log_channel_id")
        role_id = config.get("admin_role_id")

        channel_text = (
            f"<#{channel_id}>"
            if channel_id
            else "Não configurado"
        )

        role_text = (
            f"<@&{role_id}>"
            if role_id
            else "Somente administradores"
        )

        categories = "\n".join(
            f"• {CATEGORY_LABELS[key]}: "
            f"{'Ativa' if enabled else 'Desativada'}"
            for key, enabled in config["categories"].items()
        )

        await interaction.response.send_message(
            f"**Canal de registros:** {channel_text}\n"
            f"**Cargo autorizado:** {role_text}\n\n"
            f"{categories}",
            ephemeral=True,
        )
        return

    if acao.value == "canal":
        if canal is None:
            await interaction.response.send_message(
                "Informe o canal de registros.",
                ephemeral=True,
            )
            return

        permissions = canal.permissions_for(interaction.guild.me)

        if not permissions.send_messages or not permissions.embed_links:
            await interaction.response.send_message(
                "O bot precisa de Enviar mensagens e Inserir links nesse canal.",
                ephemeral=True,
            )
            return

        await store.update(
            interaction.guild.id,
            log_channel_id=canal.id,
        )

        await interaction.response.send_message(
            f"Canal de auditoria definido: {canal.mention}.",
            ephemeral=True,
        )
        return

    if acao.value == "cargo":
        if cargo is None:
            await interaction.response.send_message(
                "Informe o cargo autorizado.",
                ephemeral=True,
            )
            return

        await store.update(
            interaction.guild.id,
            admin_role_id=cargo.id,
        )

        await interaction.response.send_message(
            f"{cargo.mention} agora pode administrar o sistema.",
            ephemeral=True,
        )
        return

    if acao.value == "categoria":
        if categoria is None or ativo is None:
            await interaction.response.send_message(
                "Informe a categoria e o estado desejado.",
                ephemeral=True,
            )
            return

        categories = config["categories"].copy()
        categories[categoria.value] = ativo

        await store.update(
            interaction.guild.id,
            categories=categories,
        )

        status = "ativada" if ativo else "desativada"

        await interaction.response.send_message(
            f"Categoria {CATEGORY_LABELS[categoria.value]} {status}.",
            ephemeral=True,
        )


async def main():
    token = os.getenv("DISCORD_TOKEN", "").strip()

    if not token or token == "COLOQUE_O_TOKEN_AQUI":
        raise RuntimeError(
            "Configure DISCORD_TOKEN nas variáveis de ambiente."
        )

    await store.load()

    async with bot:
        await bot.start(token)


if __name__ == "__main__":
    asyncio.run(main())
