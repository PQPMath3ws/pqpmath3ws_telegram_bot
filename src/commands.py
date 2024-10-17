from asyncio import sleep
from database import Database
from datetime import datetime
from hashlib import md5
from random import uniform
from telegram import KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import CallbackContext, CommandHandler, filters, MessageHandler


class Commands:
    proposal_message: str = (
        "Por favor, descreva abaixo, com detalhes sobre sua proposta de site, bot, ou aplicativo que tem em mente, para desenvolver. "
    )

    def __init__(self, bot, db: Database, proposal_chat_id: int) -> None:
        self.bot = bot
        self.db = db
        self.users_states = db.get_users_states()
        self.proposal_chat_id = proposal_chat_id

    def __checkAndUpdateUser(self, update: Update, user_state: str) -> None:
        has_user = self.db.check_user_exists(user_id=update.message.from_user.id)
        if not has_user:
            self.db.create_user(
                user_id=update.message.from_user.id,
                username=update.message.from_user.username,
                chat_id=update.message.chat_id,
            )
            self.users_states[update.message.from_user.id] = {
                "chat_id": update.message.chat_id,
                "username": update.message.from_user.username,
                "user_state": user_state,
            }
        else:
            self.db.update_user(
                user_id=update.message.from_user.id,
                username=update.message.from_user.username,
                chat_id=update.message.chat_id,
                user_state=user_state,
            )
            self.users_states[update.message.from_user.id] = {
                "chat_id": update.message.chat_id,
                "username": update.message.from_user.username,
                "user_state": user_state,
            }

    async def __handle_message(self, update: Update, context: CallbackContext) -> None:
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
            elif update.message.text.strip() == "🌐 Portfólio DEV":
                await self.bot.bot.send_chat_action(
                    chat_id=update.effective_chat.id, action="typing"
                )
                random_time = uniform(5.0, 9.0)
                await sleep(random_time)
                await update.message.reply_text(
                    text=f"Obrigado pelo interesse!\n\nSegue abaixo o link do meu website, contendo um breve resumo de quem sou e dos projetos que já fiz, como dev!\n\nhttps://mathews.com.br/\n\nNo mais, é só chamar!",
                    reply_to_message_id=update.message.id,
                )
            else:
                await self.bot.bot.send_chat_action(
                    chat_id=update.effective_chat.id, action="typing"
                )
                random_time = uniform(1.2, 2.0)
                await sleep(random_time)
                await update.message.reply_text(
                    text="Opção inválida - Tente Novamente.",
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

    async def __startChat(self, update: Update, context: CallbackContext) -> None:
        keyboard_actions = [
            [
                KeyboardButton(text="📝 Fazer proposta de site / bot / aplicativo"),
            ],
            [
                KeyboardButton(text="🌐 Portfólio DEV"),
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

    async def __startProposal(self, update: Update, context: CallbackContext) -> None:
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
        self, update: Update, context: CallbackContext
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
        self, update: Update, context: CallbackContext, proposal_id: str
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
                text="Opção inválida - Tente Novamente.",
                reply_to_message_id=update.message.id,
            )

    def apply_commands(self) -> None:
        self.bot.add_handler(handler=CommandHandler("start", self.__startChat))
        self.bot.add_handler(
            handler=MessageHandler(
                filters.TEXT & ~filters.COMMAND, self.__handle_message
            )
        )
