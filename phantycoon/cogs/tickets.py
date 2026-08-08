import asyncio
import io
import re
from datetime import datetime, timezone

import disnake

from phantycoon.bot import bot
from phantycoon.config import EMBED_COLOR
from phantycoon.database import (
    close_ticket_record, count_open_tickets, create_ticket_record, get_open_ticket,
)
from phantycoon.interactions import safe_defer, safe_embed, safe_send


TICKET_PANEL_CHANNEL_ID = 1535557971424051200
TICKET_PANEL_MESSAGE_ID = 1535560318154051696
TICKET_CATEGORY_ID = 1535557923164397648
TICKET_LOG_CHANNEL_ID = 1535562644851920957
TICKET_STAFF_ROLE_IDS = {
    1535558201611915264, 1535558274009796669,
    1535562747096465510,
}
MAX_OPEN_TICKETS = 3

TICKET_TYPES = {
    "bot_support": {
        "label": "🤖 Bot Support", "short": "bot-support",
        "description": "Technical help with the bot, commands, errors, or missing functionality.",
        "questions": (
            ("issue", "What exactly is not working?", "Describe the problem in detail.", True),
            ("location", "Affected command or feature", "Example: /mine, clan invites, shop button", True),
            ("steps", "How can we reproduce it?", "List the steps that cause the problem.", True),
            ("expected", "Expected and actual result", "What should happen, and what happens instead?", True),
            ("evidence", "Errors or evidence", "Error text, message link, screenshot/video link, if available", False),
        ),
    },
    "server_support": {
        "label": "💬 Server Support", "short": "server-support",
        "description": "Help with roles, channels, permissions, verification, or the support server.",
        "questions": (
            ("request", "What do you need help with?", "Explain the server-related issue or request.", True),
            ("area", "Affected channel, role, or area", "Mention its name or provide its ID.", True),
            ("started", "When did the issue begin?", "Include approximate date/time and what changed.", False),
            ("attempts", "What have you already tried?", "Tell us what you tried so we do not repeat it.", True),
            ("resolution", "What outcome do you need?", "Describe the resolution you expect from staff.", True),
        ),
    },
    "bot_suggestion": {
        "label": "💡 Bot Suggestion", "short": "bot-suggestion",
        "description": "Suggest a new bot feature or an improvement to an existing system.",
        "questions": (
            ("title", "Suggestion title", "A short, clear name for your idea.", True),
            ("problem", "What problem does it solve?", "Explain what is currently missing or frustrating.", True),
            ("proposal", "How should it work?", "Describe the complete player flow and mechanics.", True),
            ("balance", "Balance and possible abuse", "Costs, cooldowns, limits, exploits, or side effects.", True),
            ("benefit", "Why would players benefit?", "Who benefits and how does it improve the bot?", True),
        ),
    },
    "server_suggestion": {
        "label": "🌐 Server Suggestion", "short": "server-suggestion",
        "description": "Suggest improvements for the community or support server.",
        "questions": (
            ("title", "Suggestion title", "A short and recognizable title.", True),
            ("area", "What server area changes?", "Channels, roles, events, rules, moderation, etc.", True),
            ("proposal", "Describe the proposed change", "Explain exactly what staff should add or change.", True),
            ("benefit", "How does the community benefit?", "Explain the value for members and staff.", True),
            ("implementation", "How could it be implemented?", "Optional steps, permissions, structure, or examples.", False),
        ),
    },
    "user_report": {
        "label": "🚨 User Report", "short": "user-report",
        "description": "Privately report abuse, scams, exploits, or rule violations.",
        "questions": (
            ("reported_user", "Who are you reporting?", "Provide the Discord user ID and username.", True),
            ("violation", "What rule was violated?", "Describe the incident factually and completely.", True),
            ("where_when", "Where and when did it happen?", "Channel/message link and approximate date/time.", True),
            ("evidence", "Evidence links", "Message links, screenshots, videos, or other proof.", True),
            ("risk", "Is anyone currently at risk?", "Mention ongoing scams, threats, raids, or urgent concerns.", False),
        ),
    },
    "ban_appeal": {
        "label": "⚖️ Bot Ban Appeal", "short": "ban-appeal",
        "description": "Appeal a bot restriction or captcha ban.",
        "questions": (
            ("ban_info", "Ban reason and date", "Copy the shown reason and give the approximate ban date.", True),
            ("events", "What happened?", "Explain the events honestly from your perspective.", True),
            ("appeal", "Why should the ban be removed?", "Give a specific reason for staff to reconsider it.", True),
            ("changes", "What will change going forward?", "Explain how you will prevent the issue recurring.", True),
            ("evidence", "Supporting evidence", "Relevant message, image, or video links, if available.", False),
        ),
    },
}

_creation_locks = {}


def is_ticket_staff(member):
    return isinstance(member, disnake.Member) and any(role.id in TICKET_STAFF_ROLE_IDS for role in member.roles)


def clean_channel_name(value):
    value = re.sub(r"[^a-z0-9-]", "-", value.lower())
    return re.sub(r"-+", "-", value).strip("-")[:30] or "user"


class TicketPanelView(disnake.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        for ticket_type, config in TICKET_TYPES.items():
            self.add_item(TicketTypeButton(ticket_type, config["label"]))


class TicketTypeButton(disnake.ui.Button):
    def __init__(self, ticket_type, label):
        super().__init__(label=label.split(" ", 1)[-1], style=disnake.ButtonStyle.primary, custom_id=f"ticket:create:{ticket_type}")
        self.ticket_type = ticket_type

    async def callback(self, inter):
        if not inter.guild or inter.channel.id != TICKET_PANEL_CHANNEL_ID:
            await safe_embed(inter, "Tickets", "Tickets can only be created in the support server.", ephemeral=True)
            return
        if count_open_tickets(inter.author.id) >= MAX_OPEN_TICKETS:
            await safe_embed(inter, "Ticket limit reached", f"You can have at most **{MAX_OPEN_TICKETS}** open tickets.", ephemeral=True)
            return
        await inter.response.send_modal(TicketFormModal(self.ticket_type))


class TicketFormModal(disnake.ui.Modal):
    def __init__(self, ticket_type):
        config = TICKET_TYPES[ticket_type]
        components = []
        for key, label, placeholder, required in config["questions"]:
            components.append(disnake.ui.TextInput(
                label=label, custom_id=key, placeholder=placeholder,
                style=disnake.TextInputStyle.paragraph, required=required,
                min_length=3 if required else None, max_length=1000,
            ))
        super().__init__(title=config["label"], custom_id=f"ticket:form:{ticket_type}", components=components)
        self.ticket_type = ticket_type

    async def callback(self, inter):
        lock = _creation_locks.setdefault(inter.author.id, asyncio.Lock())
        async with lock:
            if count_open_tickets(inter.author.id) >= MAX_OPEN_TICKETS:
                await safe_embed(inter, "Ticket limit reached", f"You can have at most **{MAX_OPEN_TICKETS}** open tickets.", ephemeral=True)
                return
            await safe_defer(inter, ephemeral=True)
            category = inter.guild.get_channel(TICKET_CATEGORY_ID)
            if not isinstance(category, disnake.CategoryChannel):
                await safe_embed(inter, "Ticket error", "The configured ticket category could not be found.", ephemeral=True)
                return

            overwrites = {
                inter.guild.default_role: disnake.PermissionOverwrite(view_channel=False),
                inter.author: disnake.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True, attach_files=True),
                inter.guild.me: disnake.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True, read_message_history=True),
            }
            for role_id in TICKET_STAFF_ROLE_IDS:
                role = inter.guild.get_role(role_id)
                if role:
                    overwrites[role] = disnake.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True, attach_files=True)

            config = TICKET_TYPES[self.ticket_type]
            channel = await inter.guild.create_text_channel(
                name=f"{config['short']}-{clean_channel_name(inter.author.name)}",
                category=category, overwrites=overwrites,
                topic=f"Ticket owner: {inter.author.id} | Type: {self.ticket_type}",
                reason=f"Ticket opened by {inter.author} ({inter.author.id})",
            )
            ticket_id = create_ticket_record(channel.id, inter.guild.id, inter.author.id, self.ticket_type)
            embed = disnake.Embed(
                title=f"Ticket #{ticket_id} — {config['label']}",
                description=f"Opened by {inter.author.mention}\n{config['description']}\n\nA staff member will respond as soon as possible.",
                color=EMBED_COLOR,
                timestamp=datetime.now(timezone.utc),
            )
            answers = inter.text_values
            for key, label, _, _ in config["questions"]:
                embed.add_field(name=label, value=answers.get(key) or "Not provided", inline=False)
            staff_mentions = " ".join(f"<@&{role_id}>" for role_id in TICKET_STAFF_ROLE_IDS)
            await channel.send(content=f"{inter.author.mention} {staff_mentions}", embed=embed, view=TicketControlsView())
            await safe_send(inter, f"Your ticket was created: {channel.mention}", ephemeral=True)


class TicketControlsView(disnake.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @disnake.ui.button(label="Claim", style=disnake.ButtonStyle.primary, custom_id="ticket:claim")
    async def claim(self, button, inter):
        if not is_ticket_staff(inter.author):
            await safe_embed(inter, "Access denied", "Only ticket staff can manage tickets.", ephemeral=True)
            return
        ticket = get_open_ticket(inter.channel.id)
        if not ticket:
            await safe_embed(inter, "Ticket", "This ticket is no longer active.", ephemeral=True)
            return
        await safe_embed(inter, "Ticket claimed", f"This ticket is now handled by {inter.author.mention}.")

    @disnake.ui.button(label="Close", style=disnake.ButtonStyle.primary, custom_id="ticket:close")
    async def close(self, button, inter):
        if not is_ticket_staff(inter.author):
            await safe_embed(inter, "Access denied", "Only ticket staff can manage tickets.", ephemeral=True)
            return
        if not get_open_ticket(inter.channel.id):
            await safe_embed(inter, "Ticket", "This ticket is no longer active.", ephemeral=True)
            return
        await inter.response.send_modal(CloseTicketModal())


class CloseTicketModal(disnake.ui.Modal):
    def __init__(self):
        super().__init__(
            title="Close ticket", custom_id="ticket:close-form",
            components=[disnake.ui.TextInput(
                label="Reason for closing", custom_id="reason",
                placeholder="Resolution, duplicate, invalid report, etc.",
                style=disnake.TextInputStyle.paragraph, min_length=3, max_length=500,
            )],
        )

    async def callback(self, inter):
        if not is_ticket_staff(inter.author):
            await safe_embed(inter, "Access denied", "Only ticket staff can manage tickets.", ephemeral=True)
            return
        ticket = get_open_ticket(inter.channel.id)
        if not ticket:
            await safe_embed(inter, "Ticket", "This ticket is no longer active.", ephemeral=True)
            return
        await safe_defer(inter, ephemeral=True)
        reason = inter.text_values["reason"].strip()
        log_channel = inter.guild.get_channel(TICKET_LOG_CHANNEL_ID)
        if not log_channel:
            try:
                log_channel = await bot.fetch_channel(TICKET_LOG_CHANNEL_ID)
            except disnake.DiscordException:
                await safe_embed(inter, "Ticket error", "The ticket log channel is unavailable, so the ticket was not closed.", ephemeral=True)
                return
        messages = [message async for message in inter.channel.history(limit=500, oldest_first=True)]
        transcript_lines = []
        for message in messages:
            created = message.created_at.strftime("%Y-%m-%d %H:%M:%S UTC")
            content = message.content or "[no text]"
            attachments = " ".join(item.url for item in message.attachments)
            transcript_lines.append(f"[{created}] {message.author} ({message.author.id}): {content} {attachments}".rstrip())
            for message_embed in message.embeds:
                transcript_lines.append(f"  EMBED: {message_embed.title or '[no title]'} — {message_embed.description or ''}")
                for field in message_embed.fields:
                    transcript_lines.append(f"  {field.name}: {field.value}")
        transcript = "\n".join(transcript_lines) or "No messages were recorded."

        if not close_ticket_record(inter.channel.id, inter.author.id, reason):
            await safe_embed(inter, "Ticket", "This ticket was already closed.", ephemeral=True)
            return
        created_at = datetime.fromisoformat(ticket["created_at"])
        duration = datetime.now(timezone.utc) - created_at
        embed = disnake.Embed(title=f"Ticket #{ticket['ticket_id']} closed", color=EMBED_COLOR, timestamp=datetime.now(timezone.utc))
        embed.add_field(name="Channel", value=f"{inter.channel.name} (`{inter.channel.id}`)", inline=False)
        embed.add_field(name="Type", value=TICKET_TYPES[ticket["ticket_type"]]["label"], inline=False)
        embed.add_field(name="Opened by", value=f"<@{ticket['owner_id']}> (`{ticket['owner_id']}`)", inline=False)
        embed.add_field(name="Closed by", value=f"{inter.author.mention} (`{inter.author.id}`)", inline=False)
        embed.add_field(name="Open for", value=str(duration).split(".")[0], inline=False)
        embed.add_field(name="Messages saved", value=str(len(messages)), inline=False)
        embed.add_field(name="Close reason", value=reason, inline=False)
        file = disnake.File(io.BytesIO(transcript.encode("utf-8")), filename=f"ticket-{ticket['ticket_id']}-transcript.txt")
        await log_channel.send(embed=embed, file=file)
        await safe_send(inter, "Ticket closed. This channel will be deleted in 5 seconds.", ephemeral=True)
        await asyncio.sleep(5)
        await inter.channel.delete(reason=f"Ticket #{ticket['ticket_id']} closed by {inter.author}")


@bot.listen("on_ready")
async def register_ticket_system():
    if not getattr(bot, "_ticket_views_registered", False):
        bot.add_view(TicketPanelView())
        bot.add_view(TicketControlsView())
        bot._ticket_views_registered = True
    channel = bot.get_channel(TICKET_PANEL_CHANNEL_ID)
    if not channel:
        try:
            channel = await bot.fetch_channel(TICKET_PANEL_CHANNEL_ID)
        except disnake.DiscordException:
            return
    try:
        message = await channel.fetch_message(TICKET_PANEL_MESSAGE_ID)
        embed = disnake.Embed(
            title="Support Tickets",
            description=(
                "Choose the category that best matches your request. You will be asked specific questions before your private ticket is created.\n\n"
                f"You may have up to **{MAX_OPEN_TICKETS}** open tickets at the same time. Please provide complete and accurate information."
            ),
            color=EMBED_COLOR,
        )
        await message.edit(embed=embed, view=TicketPanelView())
    except disnake.DiscordException:
        return
