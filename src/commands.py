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
from telegram.constants import ChatAction
from telegram.error import Forbidden, TimedOut
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
    subscribers_list_initial_message: str = (
        "Aqui vai uma lista do(s) user(s) que estão inscritos na newsletter:"
    )
    no_subscribers_message: str = (
        "❌ Ainda não possuem inscritos na newsletter - Lamento :'(\n\nOBS: Para reiniciar o bot, basta digitar o comando /start novamente!"
    )
    proposal_newsletter_message: str = (
        "Por favor, digite abaixo a mensagem / o anúncio que desejas enviar aos assinantes da newsletter."
    )

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

    async def __sendMessage(
        self,
        isMardownText: bool,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        initial_range: float,
        final_range: float,
        message: str,
        willReplyMessage: bool,
        reply_markup: Any,
    ) -> bool:
        try:
            replyTextCommand = (
                update.message.reply_markdown_v2
                if isMardownText
                else update.message.reply_text
            )
            count = 0
            random_time = uniform(initial_range, final_range)
            while count < random_time:
                await self.bot.bot.send_chat_action(
                    chat_id=update.effective_chat.id, action=ChatAction.TYPING
                )
                await sleep(1)
                count += 1
            await replyTextCommand(
                text=message,
                reply_to_message_id=update.message.id if willReplyMessage else None,
                reply_markup=reply_markup if reply_markup else None,
            )
            return True
        except Forbidden:
            self.db.insertUserBloquedBot(user_id=update.effective_message.from_user.id)
            return False
        except TimedOut:
            status_send_message: bool = await self.__sendMessage(
                isMardownText=isMardownText,
                update=update,
                context=context,
                initial_range=initial_range,
                final_range=final_range,
                message=message,
                willReplyMessage=willReplyMessage,
                reply_markup=reply_markup,
            )
            return status_send_message

    def __checkAndUpdateUser(self, update: Update, user_state: str) -> None:
        has_user = self.db.check_user_exists(user_id=update.message.from_user.id)
        if not has_user:
            self.db.create_user(
                user_id=update.message.from_user.id,
                username=update.message.from_user.username,
                chat_id=update.effective_chat.id,
            )
            self.users_states[update.effective_chat.id] = {
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
            self.users_states[update.effective_chat.id] = {
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
                self.users_states[update.effective_chat.id]["user_state"]
                if update.effective_chat.id in self.users_states
                and update.message.from_user.id in self.users_states
                else "welcome_message"
            ),
        )
        current_user_state: str = self.users_states[update.effective_chat.id][
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
                await self.__sendMessage(
                    isMardownText=False,
                    update=update,
                    context=context,
                    initial_range=1.2,
                    final_range=2.0,
                    message=self.invalid_command_message,
                    willReplyMessage=True,
                    reply_markup=None,
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
        elif current_user_state.startswith("waiting_confirm_send_new_newsletter_"):
            await self.__declineOrAcceptTheNewsletter(
                update=update,
                context=context,
                newsletter_id=current_user_state.replace(
                    "waiting_confirm_send_new_newsletter_", ""
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
        elif current_user_state == "waiting_reply_send_new_newsletter":
            await self.__waitingForSendNewsletterConfirmation(
                update=update, context=context
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
        status_send_message: bool = await self.__sendMessage(
            isMardownText=False,
            update=update,
            context=context,
            initial_range=5.0,
            final_range=9.0,
            message=f"Olá, {update.message.from_user.first_name} {update.message.from_user.last_name}!\n\nFico feliz que tenha me contactado! 😁\n\nEm que posso ser útil no momento?",
            willReplyMessage=True,
            reply_markup=reply_markup,
        )
        if status_send_message:
            self.__checkAndUpdateUser(
                update=update, user_state="waiting_reply_welcome_message"
            )

    async def __startProposal(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        status_send_message: bool = await self.__sendMessage(
            isMardownText=False,
            update=update,
            context=context,
            initial_range=3.0,
            final_range=5.0,
            message=self.proposal_message,
            willReplyMessage=True,
            reply_markup=ReplyKeyboardRemove(),
        )
        if status_send_message:
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
        status_send_message: bool = await self.__sendMessage(
            isMardownText=True,
            update=update,
            context=context,
            initial_range=10.0,
            final_range=15.0,
            message=f"```\n{update.message.text}\n```Deseja confirmar a sua proposta / ideia, para fazer um orçamento?",
            willReplyMessage=True,
            reply_markup=reply_markup,
        )
        if status_send_message:
            self.__checkAndUpdateUser(
                update=update,
                user_state=f"waiting_confirm_proposal_message_{proposal_hash}",
            )

    async def __declineOrAcceptTheProposal(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE, proposal_id: str
    ) -> None:
        if update.message.text.strip() == "✅ Confirmar":
            self.db.updateStatusOfProposal(proposal_id=proposal_id, isConfirmed=1)
            status_send_message: bool = await self.__sendMessage(
                isMardownText=False,
                update=update,
                context=context,
                initial_range=5.0,
                final_range=9.0,
                message=f"Boa, {update.message.from_user.first_name} {update.message.from_user.last_name}!\n\nSua proposta foi confirmada com sucesso!\n\nEm breve entrarei em contato para darmos continuidade a esse futuro projeto!\n\nObrigado pela preferência!\n\nOBS: Para reiniciar o bot, basta digitar o comando /start novamente!",
                willReplyMessage=True,
                reply_markup=ReplyKeyboardRemove(),
            )
            if status_send_message:
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
            status_send_message: bool = await self.__sendMessage(
                isMardownText=False,
                update=update,
                context=context,
                initial_range=5.0,
                final_range=9.0,
                message=f"Ah, que pena {update.message.from_user.first_name} {update.message.from_user.last_name}!\n\nSua proposta foi cancelada com sucesso!\n\nEspero poder fazer negócio com você em breve!\n\nDe qualquer forma, obrigado pela preferência!\n\nOBS: Para reiniciar o bot, basta digitar o comando /start novamente!",
                willReplyMessage=True,
                reply_markup=ReplyKeyboardRemove(),
            )
            if status_send_message:
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
            await self.__sendMessage(
                isMardownText=False,
                update=update,
                context=context,
                initial_range=1.2,
                final_range=2.0,
                message=self.invalid_command_message,
                willReplyMessage=True,
                reply_markup=None,
            )

    async def __subscribeToNewsletter(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        has_user = self.db.check_can_newsletter_user(
            user_id=update.message.from_user.id
        )
        if has_user:
            await self.__sendMessage(
                isMardownText=False,
                update=update,
                context=context,
                initial_range=5.0,
                final_range=9.0,
                message=f"Opa, {update.message.from_user.first_name} {update.message.from_user.last_name}!\n\n✅ Você já está inscrito para receber nossa newsletter!\n\nMuito obrigado! ❤️\n\nOBS: Para reiniciar o bot, basta digitar o comando /start novamente!",
                willReplyMessage=True,
                reply_markup=None,
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
            status_send_message: bool = await self.__sendMessage(
                isMardownText=False,
                update=update,
                context=context,
                initial_range=6.0,
                final_range=10.0,
                message=f"Opa, {update.message.from_user.first_name} {update.message.from_user.last_name}!\n\nDeseja realmente assinar nossa newsletter?",
                willReplyMessage=True,
                reply_markup=reply_markup,
            )
            if status_send_message:
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
            status_send_message: bool = await self.__sendMessage(
                isMardownText=False,
                update=update,
                context=context,
                initial_range=6.0,
                final_range=10.0,
                message=f"Opa, {update.message.from_user.first_name} {update.message.from_user.last_name}!\n\nDeseja realmente cancelar nossa newsletter? 😢",
                willReplyMessage=True,
                reply_markup=reply_markup,
            )
            if status_send_message:
                self.__checkAndUpdateUser(
                    update=update, user_state="waiting_reply_unsubscribe_newsletter"
                )
        else:
            await self.__sendMessage(
                isMardownText=False,
                update=update,
                context=context,
                initial_range=5.0,
                final_range=9.0,
                message=f"Opa, {update.message.from_user.first_name} {update.message.from_user.last_name}!\n\n❌ Você não está inscrito para receber nossa newsletter ainda!\n\nDe qualquer forma, muito obrigado! ❤️\n\nOBS: Para reiniciar o bot, basta digitar o comando /start novamente!",
                willReplyMessage=True,
                reply_markup=None,
            )

    async def __declineOrAcceptNewsletter(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE, isRegister: bool
    ) -> None:
        if update.message.text.strip() == "✅ Confirmar":
            if isRegister:
                status_send_message: bool = await self.__sendMessage(
                    isMardownText=False,
                    update=update,
                    context=context,
                    initial_range=5.0,
                    final_range=9.0,
                    message=f"Você foi incluído(a) na newsletter com sucesso! ☺️\n\nAgradeço fortemente pelo seu interesse! ❤️\n\n⭐️ Em breve, começo a trazer novidades para você! ⭐️\n\nOBS: Para reiniciar o bot, basta digitar o comando /start novamente!",
                    willReplyMessage=True,
                    reply_markup=ReplyKeyboardRemove(),
                )
                if status_send_message:
                    self.db.register_user_to_newsletter(
                        user_id=update.message.from_user.id
                    )
            else:
                status_send_message: bool = await self.__sendMessage(
                    isMardownText=False,
                    update=update,
                    context=context,
                    initial_range=5.0,
                    final_range=9.0,
                    message=f"Você foi removido(a) da newsletter com sucesso! 😢\n\nA partir de agora, você não receberá mais novidades por aqui! 😪\n\nOBS: Para reiniciar o bot, basta digitar o comando /start novamente!",
                    willReplyMessage=True,
                    reply_markup=ReplyKeyboardRemove(),
                )
                if status_send_message:
                    self.db.unregister_user_to_newsletter(
                        user_id=update.message.from_user.id
                    )
            self.__checkAndUpdateUser(update=update, user_state="this_is_the_end")
        elif update.message.text.strip() == "❌ Recusar":
            status_send_message: bool = await self.__sendMessage(
                isMardownText=False,
                update=update,
                context=context,
                initial_range=5.0,
                final_range=9.0,
                message=f"Entendido, {update.message.from_user.first_name} {update.message.from_user.last_name}!\n\nSua solicitação de {"assinar a newsletter" if isRegister else "sair da newsletter"} foi cancelada com sucesso!\n\nOBS: Para reiniciar o bot, basta digitar o comando /start novamente!",
                willReplyMessage=True,
                reply_markup=ReplyKeyboardRemove(),
            )
            if status_send_message:
                self.__checkAndUpdateUser(update=update, user_state="this_is_the_end")
        else:
            await self.__sendMessage(
                isMardownText=False,
                update=update,
                context=context,
                initial_range=1.2,
                final_range=2.0,
                message=self.invalid_command_message,
                willReplyMessage=True,
                reply_markup=None,
            )

    async def __listAllSubscribers(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        if (
            update.effective_chat.id == self.owner_user_id
            or update.effective_chat.id == self.proposal_chat_id
        ):
            subscribers = self.db.getAllSubscribers()
            if subscribers:
                message = self.subscribers_list_initial_message
                for index in range(len(subscribers)):
                    message += f"\n\n{index + 1} - ✅ @{subscribers[index][0]}"
                message += "\n\nOBS: Para reiniciar o bot, basta digitar o comando /start novamente!"
                await self.__sendMessage(
                    isMardownText=False,
                    update=update,
                    context=context,
                    initial_range=5.0,
                    final_range=9.0,
                    message=message,
                    willReplyMessage=True,
                    reply_markup=None,
                )
            else:
                await self.__sendMessage(
                    isMardownText=False,
                    update=update,
                    context=context,
                    initial_range=3.0,
                    final_range=5.0,
                    message=self.no_subscribers_message,
                    willReplyMessage=True,
                    reply_markup=None,
                )

    async def __sendNewsletterToSubscribers(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        if (
            update.effective_chat.id == self.owner_user_id
            or update.effective_chat.id == self.proposal_chat_id
        ):
            subscribers = self.db.checkHasSubscribers()
            if subscribers:
                status_send_message: bool = await self.__sendMessage(
                    isMardownText=False,
                    update=update,
                    context=context,
                    initial_range=4.0,
                    final_range=6.0,
                    message=self.proposal_newsletter_message,
                    willReplyMessage=True,
                    reply_markup=ReplyKeyboardRemove(),
                )
                if status_send_message:
                    self.__checkAndUpdateUser(
                        update=update, user_state="waiting_reply_send_new_newsletter"
                    )
            else:
                await self.__sendMessage(
                    isMardownText=False,
                    update=update,
                    context=context,
                    initial_range=4.0,
                    final_range=6.0,
                    message=self.no_subscribers_message,
                    willReplyMessage=True,
                    reply_markup=ReplyKeyboardRemove(),
                )

    async def __waitingForSendNewsletterConfirmation(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        if (
            update.effective_chat.id == self.owner_user_id
            or update.effective_chat.id == self.proposal_chat_id
        ):
            newsletter_hash: str = md5(
                string=f"{update.effective_chat.id}_{datetime.now().strftime("%d/%m/%Y %H:%M:%S")}".encode(
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
            self.db.createNewsletterMessage(
                newsletter_id=newsletter_hash,
                newsletter_message=update.message.text,
            )
            status_send_message: bool = await self.__sendMessage(
                isMardownText=True,
                update=update,
                context=context,
                initial_range=10.0,
                final_range=15.0,
                message=f"```\n{update.message.text}\n```Deseja confirmar a sua mensagem / o seu anúncio, para enviar aos assinantes?",
                willReplyMessage=True,
                reply_markup=reply_markup,
            )
            if status_send_message:
                self.__checkAndUpdateUser(
                    update=update,
                    user_state=f"waiting_confirm_send_new_newsletter_{newsletter_hash}",
                )

    async def __declineOrAcceptTheNewsletter(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE, newsletter_id: str
    ) -> None:
        if (
            update.effective_chat.id == self.owner_user_id
            or update.effective_chat.id == self.proposal_chat_id
        ):
            if update.message.text.strip() == "✅ Confirmar":
                self.db.updateStatusOfNewNewsletter(
                    newsletter_id=newsletter_id, isConfirmed=1
                )
                status_start_send_newsletter: bool = await self.__sendMessage(
                    isMardownText=False,
                    update=update,
                    context=context,
                    initial_range=5.0,
                    final_range=9.0,
                    message=f"Enviando sua mensagem / o seu anúncio a todos os assinantes da newsletter - Um momento...",
                    willReplyMessage=True,
                    reply_markup=ReplyKeyboardRemove(),
                )
                if status_start_send_newsletter:
                    self.__checkAndUpdateUser(
                        update=update,
                        user_state="waiting_send_newsletters",
                    )
                    await self.__sendNewsletterToAllSubscribers(
                        update=update, context=context, newsletter_id=newsletter_id
                    )
                    status_send_success_newsletter: bool = await self.__sendMessage(
                        isMardownText=False,
                        update=update,
                        context=context,
                        initial_range=5.0,
                        final_range=9.0,
                        message=f"Mensagens / anúncios enviados com sucesso a todos os assinantes!\n\nOBS: Para reiniciar o bot, basta digitar o comando /start novamente!",
                        willReplyMessage=False,
                        reply_markup=ReplyKeyboardRemove(),
                    )
                    if status_send_success_newsletter:
                        self.__checkAndUpdateUser(
                            update=update,
                            user_state="this_is_the_end",
                        )
            elif update.message.text.strip() == "❌ Recusar":
                self.db.updateStatusOfNewNewsletter(
                    newsletter_id=newsletter_id, isConfirmed=0
                )
                status_send_message: bool = await self.__sendMessage(
                    isMardownText=False,
                    update=update,
                    context=context,
                    initial_range=5.0,
                    final_range=9.0,
                    message="Sua mensagem / anúncio foi cancelado com sucesso!\n\nNão será enviado nada a todos os assinantes!\n\nOBS: Para reiniciar o bot, basta digitar o comando /start novamente!",
                    willReplyMessage=True,
                    reply_markup=ReplyKeyboardRemove(),
                )
                if status_send_message:
                    self.__checkAndUpdateUser(
                        update=update,
                        user_state="this_is_the_end",
                    )
            else:
                await self.__sendMessage(
                    isMardownText=False,
                    update=update,
                    context=context,
                    initial_range=1.2,
                    final_range=2.0,
                    message=self.invalid_command_message,
                    willReplyMessage=True,
                    reply_markup=None,
                )

    async def __sendNewsletterToAllSubscribers(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE, newsletter_id: str
    ) -> None:
        if (
            update.effective_chat.id == self.owner_user_id
            or update.effective_chat.id == self.proposal_chat_id
        ):
            subscribers = self.db.getAllSubscribers()
            newsletter_message = self.db.getNewsletterMessage(
                newsletter_id=newsletter_id
            )
            if subscribers and newsletter_message:
                for subscriber in subscribers:
                    await self.bot.bot.send_chat_action(
                        chat_id=subscriber[1], action=ChatAction.TYPING
                    )
                    random_time = uniform(15.0, 20.0)
                    await sleep(random_time)
                    await self.bot.bot.send_message(
                        chat_id=subscriber[1],
                        text=f"Nova mensagem do @PQPMath3ws_BOT!\n________________________\n\n{newsletter_message[0]}",
                    )

    async def __portfolioDev(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        await self.__sendMessage(
            isMardownText=False,
            update=update,
            context=context,
            initial_range=5.0,
            final_range=9.0,
            message=f"Obrigado pelo interesse!\n\nSegue abaixo o link do meu website, contendo um breve resumo de quem sou e dos projetos que já fiz, como dev!\n\nhttps://mathews.com.br/\n\nNo mais, é só chamar!",
            willReplyMessage=True,
            reply_markup=None,
        )

    async def __help(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        available_commands: dict = {
            "/start": "Inicializa o bot e mostra as opções disponíveis.",
            "/subscribenewsletter": "Assina a newsletter de novidades do ADM do bot.",
            "/unsubscribenewsletter": "Remove a assinatura da newsletter de novidades do ADM do bot.",
            **(
                {
                    "/listsubscribers": "Mostra uma lista (se tiver) de usuários inscritos na newsletter do ADM do bot.",
                    "/sendNewsletterToSubscribers": "Permite enviar um anúncio através do bot, para todos os assinantes do bot.",
                }
                if update.effective_chat.id == self.owner_user_id
                or update.effective_chat.id == self.proposal_chat_id
                else {}
            ),
            "/portfolio": "Mostra uma mensagem a respeito de onde você pode encontrar informações sobre o portfolio do criador do bot como dev.",
            "/help": "Mostra a lista de comandos disponíveis para você utilizar ;)",
        }
        message: str = (
            "Aqui está uma lista de comandos que estão disponíveis para utilizar comigo:"
        )
        for command in available_commands:
            message += f"\n\n{command} - {available_commands[command]}"
        await self.__sendMessage(
            isMardownText=False,
            update=update,
            context=context,
            initial_range=6.0,
            final_range=10.0,
            message=message,
            willReplyMessage=True,
            reply_markup=None,
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
        self.bot.add_handler(
            handler=CommandHandler("listsubscribers", self.__listAllSubscribers)
        )
        self.bot.add_handler(
            handler=CommandHandler(
                "sendNewsletterToSubscribers", self.__sendNewsletterToSubscribers
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
