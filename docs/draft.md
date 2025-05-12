---

### ✅ 方案 1：結合 Twilio 和 SIP 網關（用座機撥號，Twilio 幫你中繼出去）

如果你有 SIP 功能的座機系統（像 Asterisk、FreePBX、Cisco Call Manager），可以這樣做：

#### 步驟說明：

1. **設定 Twilio SIP Domain**
   → 在 Twilio 控制台建立一個 SIP Domain（像 `sip.example.sip.twilio.com`）

2. **設定 SIP Trunk 到 Twilio**
   → 在你的 SIP 系統中，設定一個 SIP Trunk 指向 Twilio 的 SIP Domain
   → 這包含認證資訊（Username/Password）和 Twilio 提供的 IP/Domain

3. **用座機撥號，通過 Twilio 出去**
   → 當你在座機撥電話，會經過你的 PBX → 轉送給 Twilio → 再打給對方

#### 🔧 前提需求：

* ✅ 你的座機是 **VoIP 或 SIP 系統**（不能是傳統電話線）
* ✅ 你懂得設定 SIP Trunk
* ✅ 你會操作 Twilio 的 Elastic SIP Trunk 功能

---

### 📘 官方參考：

[Twilio SIP Trunking Documentation](https://www.twilio.com/docs/sip-trunking)

---



Elastic SIP trunk -> Termination SIP URI
如 mytrunk.pstn.twilio.com

如果你是公司用的座機系統（例如是接在 Asterisk、FreePBX、Cisco CallManager 或其他 IP-PBX 上），你可以透過 Twilio 的 Elastic SIP Trunk 把這些座機接出網路，撥打市話或手機。以下是整體架構和設定指南：

🏢 公司座機整合 Twilio 出話方案
✅ 環境條件：
* 你們的公司電話系統支援 SIP（大部分現代系統都支援）
* 能夠設定 SIP trunk
* 有網路可以讓 SIP 系統連線到 Twilio

🔧 設定步驟（以 FreePBX/Asterisk 為例）
1. 在 Twilio 建立 Elastic SIP Trunk
* 登入 Twilio Console： https://www.twilio.com/console/sip-trunking/trunks
* 建立一個新的 Trunk，取一個名字（例如 mycompanytrunk）
* Twilio 會產生一個 Termination SIP URI：mycompanytrunk.pstn.twilio.com
*
* 設定認證方式（IP Whitelist 或 Credential）

2. 設定 Termination（撥出）
* 在你的 IP-PBX（FreePBX 或 Asterisk）中設定一個 Trunk，將出話發送到：sip:+886912345678@mycompanytrunk.pstn.twilio.com
* 其中：
    * +886... 是國際格式的電話號碼
    * mycompanytrunk.pstn.twilio.com 是 Twilio 提供的 URI
以 Asterisk 為例：
[twilio-out]
type=peer
host=mycompanytrunk.pstn.twilio.com
transport=udp
username=你的帳號（如果用 credential）
secret=你的密碼
fromdomain=mycompanytrunk.pstn.twilio.com
insecure=port,invite
context=from-internal

3. 撥號規則（Dial Plan）
* 把符合規則的號碼導向 Twilio Trunk，例如：
exten => _0.,1,Dial(SIP/${EXTEN}@twilio-out)
或在 FreePBX 的「Outbound Routes」裡面指定這條路由走 Twilio Trunk。

4. 設定 SIP 註冊（如果你是透過帳密）
* Twilio SIP Trunk 不一定需要註冊（可以只靠 IP/Domain 驗證），但如果你選的是 Username/Password 認證方式，你可能要設定：
register => username:password@mycompanytrunk.pstn.twilio.com

📶 整體流程架構圖：
[公司座機] → [IP-PBX（Asterisk / FreePBX）]
                        ↓
               [SIP Trunk: Twilio Elastic SIP]
                        ↓
                 [Twilio PSTN Gateway]
                        ↓
                 [市話 / 手機對方]

🔒 建議安全設定：
* 只允許 Twilio IP 位址存取你的 SIP ServerTwilio IP 列表參考： https://www.twilio.com/docs/voice/sip-trunking/ip-addresses
* 使用 TLS + SRTP（Twilio 支援）


to:
sip:admin@jokerrr.sip.twilio.com


Linphone 连接Twilio的第三方 SIP 账号

Username: admin
Password: Twiliopwd123!@#
Domain: jokerrr.sip.twilio.com


curl -X POST http://localhost:5050/make-call \
  -H "Content-Type: application/json" \
  -d '{"to": "sip:jong-un@sip.linphone.org"}'

{"call_sid":"CAbc48a38895d3b5d1f5a73f3e028e5f1f"}


wscat -c wss://6bfe-14-155-107-253.ngrok-free.app/media-stream
Connected (press CTRL+C to quit)



# 承载线路（carrier）是你自己的中继（trunk）或 SIP 线路，Twilio 将通过它来处理呼叫。你可以使用 Twilio 的 BYOC（Bring Your Own Carrier）功能来实现这一点。
```python
from twilio.rest import Client

# Twilio 账户 SID 和 Auth Token
account_sid = "your_account_sid"
auth_token = "your_auth_token"
client = Client(account_sid, auth_token)

# 发起呼叫
call = client.calls.create(
    to="+1234567890",  # 目标电话号码
    from_="+0987654321",  # Twilio 号码或 BYOC 号码
    url="http://demo.twilio.com/docs/voice.xml",  # 语音 XML 处理呼叫
    byoc="your_byoc_trunk_sid"  # 指定 BYOC 中继 BYxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx, 仅当 to 是一个电话号码时有效
)

#发起的是一个 SIP 电话（比如 sip:alice@example.com），对方的服务器可能需要你进行认证
# create(
#     to="+8613800138000",
#     from_="+865571112222",
#     sip_auth_username="my-sip-user",
#     sip_auth_password="my-sip-pass",
#     method="POST",
#     status_callback="https://your.service.com/callback"
# )


print(f"Call SID: {call.sid}")
```
