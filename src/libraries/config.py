class Config:
    # 机器人QQ号
    bot_id = 'Your Bot QQ'
    # Bot的超级管理员
    superuser = ['Super User QQ']
    # ChatGPT的认证选项（1为使用账号密码，2为使用session_token）
    # 若选择了其中一个，则无需填写其他选项的对应配置
    openai_authentication = 1
    # 1-ChatGPT的账号（邮箱）
    openai_email = 'Your OpenAI Account Email'
    # 1-ChatGPT的密码
    openai_password = 'Password'
    # ChatGPT使用的代理（请务必修改为自己的代理！请确保该代理可以正常使用chat.openai.com的ChatGPT）
    openai_proxy = 'localhost'
    # 2-ChatGPT的session_token
    openai_session_token = 'Session Token'