# Telegram Bot (PoC)

Aqui jás um projeto **INTERMEDIÁRIO** em estágio **de desenvolvimento** de um bot do **Telegram**! - ***EBA!!!***

**Tecnologias/libs usadas e requiridas:**

- Python 3.8 ou superior
- asyncio (nativo)
- hashlib (nativo)
- sqlite3 (nativo)
- os (nativo)
- python-telegram-bot (lib)
- python-dotenv (lib)
- Docker (uso da tecnologia de container, para deploy em VPS)

Para executar esse projeto em ambiente local, você deve seguir os seguintes passos:

Copie o arquivo ```.env.example``` e renomeie a cópia para ```.env``` e substitua os valores necessários para rodar a aplicação

OU

Crie um arquivo ```.env``` e preencha as variáveis vazias no arquivo:

```
BOT_CLIENT_ID=
BOT_SECRET_KEY=
PROPOSALS_CHAT_ID=
```

> OBS 1: É necessário obter o id do telegram de um grupo para usar na variável de PROPOSALS_CHAT_ID. Existem bots no próprio **telegram** que conseguem obter essa informação para você.

> OBS 2: Não é necessário executar o bot em um ambiente Docker localmente. Serve mais para realizar o  deploy em uma VPS privada / servidor remoto.

**VOALÁ!** - O projeto já está sendo executado na sua máquina!

<hr>

## Comandos do bot:

Abaixo segue uma lista dos comandos disponíveis do bot até o exato momento:

|Comando|Descrição|
|:-------------:|:---------------------------------------:|
| start | Inicializa o bot e mostra as opções disponíveis. |
| subscribenewsletter | Assina a newsletter de novidades do criador do bot. |
| unsubscribenewsletter | Remove a assinatura da newsletter de novidades do criador do bot. |
| portfolio | Mostra uma mensagem a respeito de onde você pode encontrar informações sobre o portfolio do criador do bot como dev. |
| help | Mostra a lista de comandos disponíveis para você utilizar ;) |

<br>

O bot principal do projeto já está funcional e você pode interagir com ele através do link abaixo:

[**Bot do criador no telegram**](https://t.me/PQPMath3ws_BOT)

<hr>

# DICA PARA O FORK DO PROJETO

> OBS: Nesse projeto, vem incluso uma Action para realizar o deploy diretamente no servidor.

Se você desejar realizar o ***FORK*** desse projeto, lembre-se de criar as variáveis ***SECRETS*** (para *Actions*) para que tudo funcione bem.

A variáveis de ***SECRETS*** são necessárias para realizar o deploy de sua aplicação diretamente em um servidor de sua posse (ou que você tenha acesso).

As variáveis necessárias são:

```
BOT_CLIENT_ID (correspondente ao ID do seu bot do telegram - é a parte antes dos dois pontos ":")
BOT_SECRET_KEY (correspondente ao token/secret_key do seu bot do telegram - é a parte depois dos dois pontos ":")
PROPOSALS_CHAT_ID (correspondente ao ID do grupo onde você receberá as propostas enviadas por outros usuários)
REMOTE_DOCKER_HOST (correspondente ao endereço/ip do host remoto para acesso via SSH)
REMOTE_DOCKER_USER (correspondente ao usuário do host remoto para acesso via SSH)
S_PASSPHRASE (correspondente a passphrase/senha da sua chave SSH para acesso ao host remoto)
S_PRIVATE (correspondente a chave privada para acesso ao host remoto via SSH)
```