# C.I. — CENTRAL DE INTELIGÊNCIA
## CAÇA-RATOS

Bot de auditoria e comunicação para servidores Discord.

## Funcionalidades

### Auditoria automática
- Criação e exclusão de canais.
- Alterações em canais.
- Criação, exclusão e alteração de cargos.
- Alterações de permissões.
- Entrada e saída de membros.
- Alterações de apelidos e nomes.
- Banimentos e desbanimentos.
- Alterações nas configurações do servidor.

### Sistema de avisos
Comando:

/ci-avisos

Parâmetros:
- titulo
- mensagem
- canal

### Configuração da auditoria
Comando:

/ci-auditoria

Permite:
- Consultar configurações.
- Definir canal de registros.
- Definir cargo autorizado.
- Ativar ou desativar categorias.

## Instalação

Instale as dependências:

pip install -r requirements.txt

Configure as variáveis de ambiente:

DISCORD_TOKEN
DEV_GUILD_ID
CONFIG_PATH

Inicie o bot:

python bot.py

## Segurança

- Nunca compartilhe o token do bot.
- Utilize permissões mínimas necessárias.
- Restrinja os comandos administrativos.
- O bot não aplica punições automaticamente.

## Identidade

C.I. — CENTRAL DE INTELIGÊNCIA

Sistema de Inteligência | CAÇA-RATOS
