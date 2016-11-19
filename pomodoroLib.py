import discord
from discord.ext import commands
from discord.ext.commands import errors as cmdErr

def getChannelId(context : commands.Context) :
	return context.message.channel.id

def getAuthorId(context : commands.Context) :
	return context.message.author.id

def getAuthorName(context : commands.Context, nick = False) :
	condition = nick and context.message.author.nick != None
	return (context.message.author.nick if condition else context.message.author.name)

def authorHasRole(context : commands.Context, roleId : str) :
	for role in context.message.author.roles :
		if role.id == roleId :
			return True
	return False

def asObject(id : str) :
	return discord.Object(id)

def toBoolean(value : str) :
	value = value.lower()

	if value == 'true' or value == 'on' or value == 'yes' or value == 'y' :
		return True
	elif value == 'false' or value == 'off' or value == 'no' or value == 'n' :
		return False
	else :
		raise cmdErr.BadArgument

def pluralize(amnt : int, sName : str, append = "", pName = "") :

	if append != "" and pName != "" :
		return None
	if append == "" and pName == "" :
		return None

	if append != "" :
		return str(amnt) + " " + (sName if amnt == 1 else sName + append)
	if pName != "" :
		return str(amnt) + " " + (sName if amnt == 1 else pName)