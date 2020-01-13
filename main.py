import datetime
import os
import re
import sys
import logging
import json
import psycopg2
import discord
import asyncio
import ctrl_db
import subprocess
import mysql.connector
from voice_generator import creat_WAV
from discord.ext import commands
from pydub import AudioSegment
from fortune import get_predic
from time import sleep


# ログを出力
d = datetime.datetime.now()
logger = logging.getLogger('discord')
logger.setLevel(logging.WARNING)
handler = logging.FileHandler(filename='syabetaro.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

# Discord アクセストークン読み込み
with open('token.json') as f:
    df = json.load(f)

token = df['bot']
manager = int(df['manager_id'])


# コマンドプレフィックスを設定
bot = commands.Bot(command_prefix='?')

# サーバ別に各値を保持
voice = {} # ボイスチャンネルID
channel = {} # テキストチャンネルID


@bot.event
# ログイン時のイベント
async def on_ready():
    print('------')
    print('えろがっぱ起動完了')
    print("起動時刻:",'%s年%s月%s日' % (d.year, d.month, d.day),'%s時%s分%s秒' % (d.hour, d.minute, d.second))
    print('LoggingBot Ver3.5.2')
    print(bot.user.id)
    print('------')
    print('導入サーバ一覧:')
    [print(' - ' + s.name) for s in bot.guilds]
    activity = discord.Activity(name='XVIDEOS', type=discord.ActivityType.watching)
    await bot.change_presence(activity=activity)



# 標準のhelpコマンドを無効化
bot.remove_command('help')

# helpコマンドの処理
@bot.command()
async def help(ctx):
    str_id = str(ctx.guild.id)
    guild_deta = ctrl_db.get_guild(str_id)
    if isinstance(guild_deta, type(None)):
        prefix = '?'
    else:
        prefix = guild_deta.prefix
    
    embed = discord.Embed(title='えろがっぱ', description='メッセージを読み上げるBotじゃけん。')
    embed.set_thumbnail(url="https://imgur.com/undefined")
    embed.add_field(name='{}join'.format(prefix), value='ワシをボイスチャンネルに呼ぶコマンドじゃ。', inline=False)
    embed.add_field(name='{}bye'.format(prefix), value='ワシをボイスチャンネルから追い出すのにつこーたらええ。', inline=False)
    embed.add_field(name='{}set_prefix'.format(prefix), value='コマンドプレフィックスを変更すんのに使うで。「{}set_prefix ?」みたいにしんさいや。'.format(prefix), inline=False)
    embed.add_field(name='{}stop'.format(prefix), value='わいが喋ってるのを黙らせるで。', inline=False)        
    embed.add_field(name='{}wbook'.format(prefix), value='読み仮名の登録とかするやつ。詳しくは、「{}wbook help」を見ぃ！。'.format(prefix), inline=False)
    embed.add_field(name='{}uranai'.format(prefix), value='おみくじが引こー思うたら使いんさい。結果は日替わりじゃけんな。', inline=False)
    embed.add_field(name='{}poll'.format(prefix), value='投票機能じゃ！『(prefix)poll　質問　答え　答え』みたいに書きんさい。そしたら投票できるで', inline=False)
    await ctx.send(embed=embed)


# summonコマンドの処理
@bot.command()
async def join(ctx):
    global voice
    global channel
    # global guild_id
    guild_id = ctx.guild.id # サーバIDを取得
    vo_ch = ctx.author.voice # 召喚した人が参加しているボイスチャンネルを取得

    # サーバを登録
    add_guild_db(ctx.guild)

    # サーバのプレフィックスを取得
    guild_deta = ctrl_db.get_guild(str(guild_id))
    if isinstance(guild_deta, type(None)):
        prefix = '?'
    else:
        prefix = guild_deta.prefix

    # 召喚された時、voiceに情報が残っている場合
    if guild_id in voice:
        await voice[guild_id].disconnect()
        del voice[guild_id] 
        del channel[guild_id]
    # 召喚した人がボイスチャンネルにいた場合
    if not isinstance(vo_ch, type(None)): 
        voice[guild_id] = await vo_ch.channel.connect()
        channel[guild_id] = ctx.channel.id
        noties = get_notify(ctx)
        await ctx.channel.send('おっぱ～い♪ボインボイン♡')
        for noty in noties:
            await ctx.channel.send(noty)
        if len(noties) != 0:
            await ctx.channel.send('えろがっぱに何かあれば、あおちゃまでお願いすらぁ。\r完成度低いんは目を瞑ってくれ🙌')
    else :
        await ctx.channel.send('おめぇボイスチャンネルおらんじゃろうが！')

# byeコマンドの処理            
@bot.command()
async def bye(ctx):
    global guild_id
    global voice
    global channel
    guild_id = ctx.guild.id
    # コマンドが、呼び出したチャンネルで叩かれている場合
    await ctx.channel.send('ワシはけぇるで')
    await voice[guild_id].disconnect() # ボイスチャンネル切断
            # 情報を削除
    del voice[guild_id] 
    del channel[guild_id]

# speakerコマンドの処理


@bot.command()
async def set_prefix(ctx, arg1):
    # prefixの設定
    guild_id = str(ctx.guild.id)

    ctrl_db.set_prefix(guild_id, arg1)
    await ctx.send('prefixを{}に変更したで。'.format(arg1))

# ここから管理者コマンド
@bot.command()
async def notify(ctx, arg1, arg2):
    # 管理人からしか受け付けない
    if ctx.author.id != manager:
        return
    ctrl_db.add_news(arg1, arg2.replace('\\r', '\r'))

@bot.command()
async def say_adm(ctx, arg1):
    # 管理人からしか受け付けない
    if ctx.author.id != manager:
        return
    global channel

    for vc in bot.voice_clients:
        if isinstance(channel[vc.guild.id], type(None)):
            continue
        for txch in vc.guild.text_channels:
            if txch.id == channel[vc.guild.id]:
                await txch.send('[INFO] {}'.format(arg1))
# ここまで

# 喋太郎の発言を止める
@bot.command()
async def stop(ctx):
    global voice
    vc = voice[ctx.guild.id]
    await ctx.send("シンプルに口がくさい！")
    if(vc.is_playing()):
        vc.stop()

@bot.command()
async def wbook(ctx, arg1='emp', arg2='emp', arg3='emp'):
    guild_id = ctx.guild.id
    str_id = str(guild_id)
    guild_deta = ctrl_db.get_guild(str_id)
    if isinstance(guild_deta, type(None)):
        prefix = '?'
    else:
        prefix = guild_deta.prefix

    if arg1 == 'help':
        embed = discord.Embed(title='{}wbook'.format(prefix), description='辞書を操作するコマンド。データはサーバ毎に分けられてるから安心してな。')
        embed.add_field(name='{}wbook add 単語 よみがな'.format(prefix), value='読み上げ文にこの単語があった場合、よみがなの通りに読み変えるで。\r例:{}wbook add 男の娘 おとこのこ'.format(prefix), inline=False)
        embed.add_field(name='{}wbook list'.format(prefix), value='登録した単語の一覧を表示するで。', inline=False)
        embed.add_field(name='{}wbook delete 番号'.format(prefix), value='listで表示された辞書番号の単語を削除するで', inline=False)

        await ctx.send(embed=embed)

    elif arg1 == 'list':
        # リスト表示
        words = ctrl_db.get_dict(str_id)
        embed = discord.Embed(title='辞書一覧')
        embed.add_field(name='番号', value='単語:よみがな', inline=False)
        for i, word in enumerate(words, start=1):
            if i%15 == 0:
                await ctx.send(embed=embed)
                embed = discord.Embed(title=str(word.id), description='{}:{}'.format(word.word, word.read))
            else:
                embed.add_field(name=str(word.id), value='{}:{}'.format(word.word, word.read), inline=False)

        await ctx.send(embed=embed)

    elif arg1 == 'add':
        if arg2 == 'emp' or arg3 == 'emp':
            await ctx.send('引数が不足してるで。{}wbook helpを見てみ。'.format(prefix))
        # 辞書追加、あるいはアップデート
        ctrl_db.add_dict(arg2, arg3, str_id)
        await ctx.send('登録したで～')

    elif arg1 == 'delete':
        if arg2 == 'emp':
            await ctx.send('引数が不足してるで。{}wbook helpを見てみ。'.format(prefix))
        elif arg2.isdecimal():
            # 削除処理
            is_del = ctrl_db.del_dict(int(arg2), str_id)
            if is_del == True:
                await ctx.send('削除成功や。')
            else:
                await ctx.send('その番号の単語は登録されてないで。')
        else:
            await ctx.send('使い方が正しくないで。{}wbook helpを見てみ。'.format(prefix))
    else:
        await ctx.send('使い方が正しくないで。{}wbook helpを見てみ。'.format(prefix))

@bot.command()
async def readname(ctx, arg1='emp'):
    guild_id = ctx.guild.id
    str_id = str(guild_id)
    guild_deta = ctrl_db.get_guild(str_id)
    if isinstance(guild_deta, type(None)):
        prefix = '?'
    else:
        prefix = guild_deta.prefix

    if arg1 == 'emp':
        await ctx.send('引数が不足してるで。{}helpを見てみ。'.format(prefix))
    elif arg1 == 'on':
        ctrl_db.set_nameread(True, str_id)
        await ctx.send('名前を読むようにしたけん。'.format(prefix))
    elif arg1 == 'off':
        ctrl_db.set_nameread(False, str_id)
        await ctx.send('名前を読まんようにしたけん。'.format(prefix))
    else:
        ('引数が不足してるで。{}helpを見てみ。'.format(prefix))



@bot.command()
async def uranai(ctx):
    predic = get_predic(ctx.author.id)

    embed = discord.Embed(title='{}のおみくじ'.format(ctx.author.display_name))
    embed.add_field(name='運勢', value=predic['運勢'], inline=False)
    embed.add_field(name='和歌', value=predic['和歌'], inline=False)
    embed.add_field(name='願望', value=predic['願望'], inline=False)
    embed.add_field(name='健康', value=predic['健康'], inline=False)
    embed.add_field(name='待ち人', value=predic['待ち人'], inline=False)
    embed.add_field(name='出産', value=predic['出産'], inline=False)
    embed.add_field(name='商売', value=predic['商売'], inline=False)
 

    await ctx.send(embed=embed)



# メッセージを受信した時の処理
@bot.event
async def on_message(message):
    global voice
    global channel
    if message.author.bot:
        return
    import datetime
    d = datetime.datetime.now()
    print("============")
    print("サーバ名:",message.guild)
    print("投稿者：",message.author.name)
    print("Type：Message")
    print("内容：",message.content.encode('CP932', "ignore").decode("CP932"))
    print("Channel:" + str(message.channel))
    print("データ取得日時:",'%s年%s月%s日' % (d.year, d.month, d.day),'%s時%s分%s秒' % (d.hour, d.minute, d.second))
    print("============")
    mess_id = message.author.id

    # ギルドIDがない場合、DMと判断する
    if isinstance(message.guild, type(None)):
        # 管理人からのDMだった場合
        if message.author.id == manager:
            #コマンド操作になっているか
            if message.content.startswith('?'):
                await message.channel.send('コマンドを受け付けたで')
                await bot.process_commands(message) # メッセージをコマンド扱いにする
                return
            else:
                await message.channel.send('コマンド操作をしてくれ')
                return
        else:
            await message.channel.send('えろがっぱに何かあれば、おっぱい揉ませてくれ。')
            return




    guild_id = message.guild.id # サーバID
    # ユーザ情報(speaker)を取得
    user = ctrl_db.get_user(str(mess_id))
    if isinstance(user, type(None)):
        # ユーザ情報がなければ、dbへ登録。話者はsumire
        ctrl_db.add_user(str(mess_id), message.author.name, 'sumire')
        user = ctrl_db.get_user(str(mess_id))

    # サーバのプレフィックスを取得
    guild_deta = ctrl_db.get_guild(str(guild_id))
    if isinstance(guild_deta, type(None)):
        prefix = '?'
    else:
        prefix = guild_deta.prefix

    # コマンドだった場合
    if message.content.startswith(prefix):
        # prefixは?へ変換する
        message.content = message.content.replace(prefix, '?', 1)
        await bot.process_commands(message) # メッセージをコマンド扱いにする
        return

    # 召喚されていなかった場合
    if guild_id not in channel:
        return

    
    str_guild_id = str(guild_id)

    # メッセージを、呼び出されたチャンネルで受信した場合
    if message.channel.id == channel[guild_id]:
        get_msg = message.clean_content
        # URLを、"URL"へ置換
        get_msg = re.sub(r'(https?|ftp)(:\/\/[-_.!~*\'()a-zA-Z0-9;\/?:\@&=+\$,%#]+)', 'URL', get_msg)    
        # reactionの置換
        get_msg = get_msg.replace('<:', '')
        get_msg = re.sub(r'[0-9]*>', '', get_msg)        
        # 置換文字のリストを
        words = ctrl_db.get_dict(str_guild_id)
        for word in words:
            get_msg = get_msg.replace(word.word, word.read)
        get_msg = get_msg.replace('<', '').replace('>', '')
        # 読み上げモード確認
        is_nameread = ctrl_db.get_guild(str_guild_id).is_nameread
        # モードによって名前を追加するか検討
        if is_nameread == True:
            get_msg = '{}、'.format(message.author.display_name) + get_msg
        #リクエスト回数のカウント
        ctrl_db.set_reqcount(datetime.date.today(), datetime.datetime.now().hour)
        try:
            creat_WAV(get_msg)
            source = discord.FFmpegPCMAudio("output.wav")
            message.guild.voice_client.play(source)
            await asyncio.sleep(1)
            while (voice[guild_id].is_playing()):
                await asyncio.sleep(1)
        except:
            while (voice[guild_id].is_playing()):
                await asyncio.sleep(1)
                return


def add_guild_db(guild):
    str_id = str(guild.id)
    guilds = ctrl_db.get_guild(str_id)
    # デフォルトのprefixは'?'
    prefix = '?'

    if isinstance(guilds, type(None)):
        ctrl_db.add_guild(str_id, guild.name, prefix)

def get_notify(ctx):
    str_id = str(ctx.guild.id)
    notifis = ctrl_db.get_notify(str_id)
    newses = ctrl_db.get_news()
    list_noty = []

    for new in newses:
        is_notify = False
        for noty in notifis:
            if new.id == noty.news_id:
                is_notify = True
        if is_notify == False:
            list_noty.append('[{}] {}'.format(new.category, new.text))
            ctrl_db.add_notify(new.id, str_id)
    
    return list_noty


@bot.command()
async def poll(ctx, about = "question", *args):
    guild_deta = ctrl_db.get_guild(str(guild_id))
    if isinstance(guild_deta, type(None)):
        prefix = '?'
    else:
        prefix = guild_deta.prefix
    emojis = ["1⃣","2⃣","3⃣","4⃣", ':five:']

    cnt = len(args)
    message = discord.Embed(title=":speech_balloon: "+about,colour=0x1e90ff)
    if cnt <= len(emojis):
        for a in range(cnt):
            message.add_field(name=f'{emojis[a]}{args[a]}', value="** **", inline=False)
        msg = await ctx.send(embed=message)
        #投票の欄
        for i in range(cnt):
            await msg.add_reaction(emojis[i])
    else:
        await ctx.send("すまないが項目は5つまでなんだ...")



bot.run(token)