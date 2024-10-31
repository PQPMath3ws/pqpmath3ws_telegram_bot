from asyncio import sleep
from database import Database
from datetime import datetime
from hashlib import md5
from random import uniform
from telegram import (
    ChatMember,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    Update,
)
from telegram.ext import (
    Application,
    ChatMemberHandler,
    CommandHandler,
    ContextTypes,
    ExtBot,
    filters,
    JobQueue,
    MessageHandler,
)
from typing import Any, Dict


class Commands:
    proposal_message: str = (
        "Por favor, descreva abaixo, com detalhes sobre sua proposta de site, bot, ou aplicativo que tem em mente, para desenvolver. "
    )
    invalid_command_message: str = "Opção inválida."

    def __init__(
        self,
        bot: Application[
            ExtBot[None],
            ContextTypes.DEFAULT_TYPE,
            Dict[Any, Any],
            Dict[Any, Any],
            Dict[Any, Any],
            JobQueue[ContextTypes.DEFAULT_TYPE],
        ],
        db: Database,
        proposal_chat_id: int,
        owner_user_id: int,
    ) -> None:
        self.bot = bot
        self.db = db
        self.users_states = db.get_users_states()
        self.proposal_chat_id = proposal_chat_id
        self.owner_user_id = owner_user_id

    def __checkAndUpdateUser(self, update: Update, user_state: str) -> None:
        has_user = self.db.check_user_exists(user_id=update.message.from_user.id)
        if not has_user:
            self.db.create_user(
                user_id=update.message.from_user.id,
                username=update.message.from_user.username,
                chat_id=update.effective_chat.id,
            )
            self.users_states[update.message.from_user.id] = {
                "chat_id": update.effective_chat.id,
                "username": update.message.from_user.username,
                "user_state": user_state,
            }
        else:
            self.db.update_user(
                user_id=update.message.from_user.id,
                username=update.message.from_user.username,
                chat_id=update.effective_chat.id,
                user_state=user_state,
            )
            self.users_states[update.message.from_user.id] = {
                "chat_id": update.effective_chat.id,
                "username": update.message.from_user.username,
                "user_state": user_state,
            }

    async def __handle_message(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        self.__checkAndUpdateUser(
            update=update,
            user_state=(
                self.users_states[update.message.from_user.id]["user_state"]
                if update.message.from_user.id in self.users_states
                else "welcome_message"
            ),
        )
        current_user_state: str = self.users_states[update.message.from_user.id][
            "user_state"
        ]
        if current_user_state == "welcome_message":
            await self.__startChat(update=update, context=context)
        elif current_user_state == "waiting_reply_welcome_message":
            if (
                update.message.text.strip()
                == "📝 Fazer proposta de site / bot / aplicativo"
            ):
                await self.__startProposal(update=update, context=context)
            elif update.message.text.strip() == "📩 Assinar newsletter":
                await self.__subscribeToNewsletter(update=update, context=context)
            elif update.message.text.strip() == "🚫 Cancelar newsletter":
                await self.__unsubscribeToNewsletter(update=update, context=context)
            elif update.message.text.strip() == "🌐 Portfólio DEV":
                await self.__portfolioDev(update=update, context=context)
            elif update.message.text.strip() == "❓ Ajuda":
                await self.__help(update=update, context=context)
            else:
                await self.bot.bot.send_chat_action(
                    chat_id=update.effective_chat.id, action="typing"
                )
                random_time = uniform(1.2, 2.0)
                await sleep(random_time)
                await update.message.reply_text(
                    text=self.invalid_command_message,
                    reply_to_message_id=update.message.id,
                )
        elif current_user_state == "waiting_reply_proposal_message":
            await self.__waitingForProposalConfirmation(update=update, context=context)
        elif current_user_state.startswith("waiting_confirm_proposal_message_"):
            await self.__declineOrAcceptTheProposal(
                update=update,
                context=context,
                proposal_id=current_user_state.replace(
                    "waiting_confirm_proposal_message_", ""
                ),
            )
        elif current_user_state == "waiting_reply_subscribe_newsletter":
            await self.__declineOrAcceptNewsletter(
                update=update, context=context, isRegister=True
            )
        elif current_user_state == "waiting_reply_unsubscribe_newsletter":
            await self.__declineOrAcceptNewsletter(
                update=update, context=context, isRegister=False
            )

    async def __enteringOnChat(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        if update.my_chat_member.new_chat_member.status == ChatMember.MEMBER:
            if update.effective_chat.id != self.proposal_chat_id:
                await self.bot.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text="Esse bot não pode ser adicionado em grupos - Saindo...",
                )
                await update.effective_chat.leave()
            else:
                await self.bot.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text="Agora, para obter a total funcionalidade desse bot, coloque-me como administrador do grupo, para que eu consiga interagir por aqui também ;)",
                )
        elif update.my_chat_member.new_chat_member.status == ChatMember.ADMINISTRATOR:
            await self.bot.bot.send_message(
                chat_id=update.effective_chat.id,
                text="Tudo configurado de forma correta agora - Bom proveito ;)",
            )

    async def __startChat(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        keyboard_actions = [
            [
                KeyboardButton(text="📝 Fazer proposta de site / bot / aplicativo"),
            ],
            [
                KeyboardButton(text="📩 Assinar newsletter"),
                KeyboardButton(text="🚫 Cancelar newsletter"),
            ],
            [
                KeyboardButton(text="🌐 Portfólio DEV"),
            ],
            [
                KeyboardButton(text="❓ Ajuda"),
            ],
        ]
        reply_markup = ReplyKeyboardMarkup(
            keyboard=keyboard_actions, one_time_keyboard=False, resize_keyboard=True
        )
        await self.bot.bot.send_chat_action(
            chat_id=update.effective_chat.id, action="typing"
        )
        random_time = uniform(5.0, 9.0)
        await sleep(random_time)
        await update.message.reply_text(
            text=f"Olá, {update.message.from_user.first_name} {update.message.from_user.last_name}!\n\nFico feliz que tenha me contactado! 😁\n\nEm que posso ser útil no momento?",
            reply_to_message_id=update.message.id,
            reply_markup=reply_markup,
        )
        self.__checkAndUpdateUser(
            update=update, user_state="waiting_reply_welcome_message"
        )

    async def __startProposal(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        await self.bot.bot.send_chat_action(
            chat_id=update.effective_chat.id, action="typing"
        )
        random_time = uniform(3.0, 5.0)
        await sleep(random_time)
        await update.message.reply_text(
            text=self.proposal_message,
            reply_to_message_id=update.message.id,
            reply_markup=ReplyKeyboardRemove(),
        )
        self.__checkAndUpdateUser(
            update=update, user_state="waiting_reply_proposal_message"
        )

    async def __waitingForProposalConfirmation(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        proposal_hash: str = md5(
            string=f"{update.message.from_user.username}_{datetime.now().strftime("%d/%m/%Y %H:%M:%S")}".encode(
                "utf-8"
            )
        ).hexdigest()
        keyboard_actions = [
            [
                KeyboardButton(text="✅ Confirmar"),
                KeyboardButton(text="❌ Recusar"),
            ],
        ]
        reply_markup = ReplyKeyboardMarkup(
            keyboard=keyboard_actions, one_time_keyboard=False, resize_keyboard=True
        )
        self.db.createProposal(
            proposal_id=proposal_hash,
            user_id=update.message.from_user.id,
            proposal=update.message.text,
        )
        await self.bot.bot.send_chat_action(
            chat_id=update.effective_chat.id, action="typing"
        )
        random_time = uniform(10.0, 15.0)
        await sleep(random_time)
        await update.message.reply_markdown_v2(
            text=f"```\n{update.message.text}\n```Deseja confirmar a sua proposta / ideia, para fazer um orçamento?",
            reply_markup=reply_markup,
        )
        self.__checkAndUpdateUser(
            update=update,
            user_state=f"waiting_confirm_proposal_message_{proposal_hash}",
        )

    async def __declineOrAcceptTheProposal(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE, proposal_id: str
    ) -> None:
        if update.message.text.strip() == "✅ Confirmar":
            self.db.updateStatusOfProposal(proposal_id=proposal_id, isConfirmed=1)
            await self.bot.bot.send_chat_action(
                chat_id=update.effective_chat.id, action="typing"
            )
            random_time = uniform(5.0, 9.0)
            await sleep(random_time)
            await update.message.reply_text(
                text=f"Boa, {update.message.from_user.first_name} {update.message.from_user.last_name}!\n\nSua proposta foi confirmada com sucesso!\n\nEm breve entrarei em contato para darmos continuidade a esse futuro projeto!\n\nObrigado pela preferência!\n\nOBS: Para reiniciar o bot, basta digitar o comando /start novamente!",
                reply_to_message_id=update.message.id,
                reply_markup=ReplyKeyboardRemove(),
            )
            self.__checkAndUpdateUser(
                update=update,
                user_state="this_is_the_end",
            )
            proposal: dict | None = self.db.getProposal(proposal_id=proposal_id)
            if proposal:
                await self.bot.bot.send_message(
                    chat_id=self.proposal_chat_id,
                    text=f"""Nova proposta enviada!\n\nEstado da proposta: ✅ Confirmada!\n\nUsuário que enviou: @{proposal["user"]}\n\nProposta:\n\n{proposal["proposal"]}""",
                )
        elif update.message.text.strip() == "❌ Recusar":
            self.db.updateStatusOfProposal(proposal_id=proposal_id, isConfirmed=0)
            await self.bot.bot.send_chat_action(
                chat_id=update.effective_chat.id, action="typing"
            )
            random_time = uniform(5.0, 9.0)
            await sleep(random_time)
            await update.message.reply_text(
                text=f"Ah, que pena {update.message.from_user.first_name} {update.message.from_user.last_name}!\n\nSua proposta foi cancelada com sucesso!\n\nEspero poder fazer negócio com você em breve!\n\nDe qualquer forma, obrigado pela preferência!\n\nOBS: Para reiniciar o bot, basta digitar o comando /start novamente!",
                reply_to_message_id=update.message.id,
                reply_markup=ReplyKeyboardRemove(),
            )
            self.__checkAndUpdateUser(
                update=update,
                user_state="this_is_the_end",
            )
            proposal: dict | None = self.db.getProposal(proposal_id=proposal_id)
            if proposal:
                await self.bot.bot.send_message(
                    chat_id=self.proposal_chat_id,
                    text=f"""Nova proposta enviada!\n\nEstado da proposta: ❌ Recusada!\n\nUsuário que enviou: @{proposal["user"]}\n\nProposta:\n\n{proposal["proposal"]}""",
                )
        else:
            await self.bot.bot.send_chat_action(
                chat_id=update.effective_chat.id, action="typing"
            )
            random_time = uniform(1.2, 2.0)
            await sleep(random_time)
            await update.message.reply_text(
                text=self.invalid_command_message,
                reply_to_message_id=update.message.id,
            )

    async def __subscribeToNewsletter(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        has_user = self.db.check_can_newsletter_user(
            user_id=update.message.from_user.id
        )
        if has_user:
            await self.bot.bot.send_chat_action(
                chat_id=update.effective_chat.id, action="typing"
            )
            random_time = uniform(5.0, 9.0)
            await sleep(random_time)
            await update.message.reply_text(
                text=f"Opa, {update.message.from_user.first_name} {update.message.from_user.last_name}!\n\n✅ Você já está inscrito para receber nossa newsletter!\n\nMuito obrigado! ❤️\n\nOBS: Para reiniciar o bot, basta digitar o comando /start novamente!",
                reply_to_message_id=update.message.id,
            )
        else:
            keyboard_actions = [
                [
                    KeyboardButton(text="✅ Confirmar"),
                    KeyboardButton(text="❌ Recusar"),
                ],
            ]
            reply_markup = ReplyKeyboardMarkup(
                keyboard=keyboard_actions, one_time_keyboard=False, resize_keyboard=True
            )
            await self.bot.bot.send_chat_action(
                chat_id=update.effective_chat.id, action="typing"
            )
            random_time = uniform(6.0, 10.0)
            await sleep(random_time)
            await update.message.reply_text(
                text=f"Opa, {update.message.from_user.first_name} {update.message.from_user.last_name}!\n\n❓ Deseja realmente assinar nossa newsletter? ❓",
                reply_to_message_id=update.message.id,
                reply_markup=reply_markup,
            )
            self.__checkAndUpdateUser(
                update=update, user_state="waiting_reply_subscribe_newsletter"
            )

    async def __unsubscribeToNewsletter(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        has_user = self.db.check_can_newsletter_user(
            user_id=update.message.from_user.id
        )
        if has_user:
            keyboard_actions = [
                [
                    KeyboardButton(text="✅ Confirmar"),
                    KeyboardButton(text="❌ Recusar"),
                ],
            ]
            reply_markup = ReplyKeyboardMarkup(
                keyboard=keyboard_actions, one_time_keyboard=False, resize_keyboard=True
            )
            await self.bot.bot.send_chat_action(
                chat_id=update.effective_chat.id, action="typing"
            )
            random_time = uniform(6.0, 10.0)
            await sleep(random_time)
            await update.message.reply_text(
                text=f"Opa, {update.message.from_user.first_name} {update.message.from_user.last_name}!\n\n❓ Deseja realmente cancelar nossa newsletter? 😢 ❓",
                reply_to_message_id=update.message.id,
                reply_markup=reply_markup,
            )
            self.__checkAndUpdateUser(
                update=update, user_state="waiting_reply_unsubscribe_newsletter"
            )
        else:
            await self.bot.bot.send_chat_action(
                chat_id=update.effective_chat.id, action="typing"
            )
            random_time = uniform(5.0, 9.0)
            await sleep(random_time)
            await update.message.reply_text(
                text=f"Opa, {update.message.from_user.first_name} {update.message.from_user.last_name}!\n\n❌ Você não está inscrito para receber nossa newsletter ainda!\n\nDe qualquer forma, muito obrigado! ❤️\n\nOBS: Para reiniciar o bot, basta digitar o comando /start novamente!",
                reply_to_message_id=update.message.id,
            )

    async def __declineOrAcceptNewsletter(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE, isRegister: bool
    ) -> None:
        if update.message.text.strip() == "✅ Confirmar":
            await self.bot.bot.send_chat_action(
                chat_id=update.effective_chat.id, action="typing"
            )
            random_time = uniform(5.0, 9.0)
            await sleep(random_time)
            if isRegister:
                await update.message.reply_text(
                    text=f"Você foi incluído(a) na newsletter com sucesso! ☺️\n\nAgradeço fortemente pelo seu interesse! ❤️\n\n⭐️ Em breve, começo a trazer novidades para você! ⭐️\n\nOBS: Para reiniciar o bot, basta digitar o comando /start novamente!",
                    reply_to_message_id=update.message.id,
                    reply_markup=ReplyKeyboardRemove(),
                )
                self.db.register_user_to_newsletter(user_id=update.message.from_user.id)
            else:
                await update.message.reply_text(
                    text=f"Você foi removido(a) da newsletter com sucesso! 😢\n\nA partir de agora, você não receberá mais novidades por aqui! 😪\n\nOBS: Para reiniciar o bot, basta digitar o comando /start novamente!",
                    reply_to_message_id=update.message.id,
                    reply_markup=ReplyKeyboardRemove(),
                )
                self.db.unregister_user_to_newsletter(
                    user_id=update.message.from_user.id
                )
            self.__checkAndUpdateUser(update=update, user_state="this_is_the_end")
        elif update.message.text.strip() == "❌ Recusar":
            await self.bot.bot.send_chat_action(
                chat_id=update.effective_chat.id, action="typing"
            )
            random_time = uniform(5.0, 9.0)
            await sleep(random_time)
            await update.message.reply_text(
                text=f"Entendido, {update.message.from_user.first_name} {update.message.from_user.last_name}!\n\nSua solicitação de {"assinar a newsletter" if isRegister else "sair da newsletter"} foi cancelada com sucesso!\n\nOBS: Para reiniciar o bot, basta digitar o comando /start novamente!",
                reply_to_message_id=update.message.id,
                reply_markup=ReplyKeyboardRemove(),
            )
            self.__checkAndUpdateUser(update=update, user_state="this_is_the_end")
        else:
            await self.bot.bot.send_chat_action(
                chat_id=update.effective_chat.id, action="typing"
            )
            random_time = uniform(1.2, 2.0)
            await sleep(random_time)
            await update.message.reply_text(
                text=self.invalid_command_message,
                reply_to_message_id=update.message.id,
            )

    async def __portfolioDev(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        await self.bot.bot.send_chat_action(
            chat_id=update.effective_chat.id, action="typing"
        )
        random_time = uniform(5.0, 9.0)
        await sleep(random_time)
        await update.message.reply_text(
            text=f"Obrigado pelo interesse!\n\nSegue abaixo o link do meu website, contendo um breve resumo de quem sou e dos projetos que já fiz, como dev!\n\nhttps://mathews.com.br/\n\nNo mais, é só chamar!",
            reply_to_message_id=update.message.id,
        )

    async def __help(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        available_commands: dict = {
            "/start": "Inicializa o bot e mostra as opções disponíveis.",
            "/subscribenewsletter": "Assina a newsletter de novidades do ADM do bot.",
            "/unsubscribenewsletter": "Remove a assinatura da newsletter de novidades do ADM do bot.",
            "/portfolio": "Mostra uma mensagem a respeito de onde você pode encontrar informações sobre o portfolio do criador do bot como dev.",
            "/help": "Mostra a lista de comandos disponíveis para você utilizar ;)",
        }
        message: str = (
            "Aqui está uma lista de comandos que estão disponíveis para utilizar comigo:"
        )
        for command in available_commands:
            message += f"\n\n{command} - {available_commands[command]}"
        await self.bot.bot.send_chat_action(
            chat_id=update.effective_chat.id, action="typing"
        )
        random_time = uniform(6.0, 10.0)
        await sleep(random_time)
        await update.message.reply_text(
            text=message, reply_to_message_id=update.message.id
        )

    def apply_commands(self) -> None:
        self.bot.add_handler(handler=CommandHandler("start", self.__startChat))
        self.bot.add_handler(
            handler=CommandHandler("subscribenewsletter", self.__subscribeToNewsletter)
        )
        self.bot.add_handler(
            handler=CommandHandler(
                "unsubscribenewsletter", self.__unsubscribeToNewsletter
            )
        )
        self.bot.add_handler(handler=CommandHandler("portfolio", self.__portfolioDev))
        self.bot.add_handler(handler=CommandHandler("help", self.__help))
        self.bot.add_handler(
            handler=MessageHandler(
                filters.TEXT & ~filters.COMMAND, self.__handle_message
            )
        )
        self.bot.add_handler(
            handler=ChatMemberHandler(
                self.__enteringOnChat, ChatMemberHandler.MY_CHAT_MEMBER
            )
        )
