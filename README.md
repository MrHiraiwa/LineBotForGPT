# LineBotForGPT

このリポジトリは、LINE上で動作するPythonベースのチャットボットです。このボットはChatGPT APIを使用して、ユーザからのメッセージに対してレスポンスを生成します。

## 環境変数
以下の機能を持っています。：

- Web設定: パラメーターをWeb画面で設定可能です。コードを変更する必要はありません。
- ボット会話: 設定したキャラクター性でChatGPTと会話できます。グループチャットにも対応します。
- Web検索: Google Custom Searchを用いてWeb検索が行えます。
- 画像認識: Cloud Visionを用いて画像認識が行なえます。

## セットアップ
以下のステップに従ってセットアップしてください：
1. Google Cloud Runでデプロイします：Google Cloud Consoleでプロジェクトを作成しCloud Run APIを有効にし、本レポジトリを指定してデプロイします。 デプロイの際は以下の環境変数を設定する必要があります。
2. 同じプロジェクト内でFirestoreを有効にします：左側のナビゲーションメニューで「Firestore」を選択し、Firestoreをプロジェクトで有効にします。
3. データベースを作成します：Firestoreダッシュボードに移動し、「データベースの作成」をクリックします。「ネイティブ」モードを選択します。
4. Custom Search、Cloud Visionの両APIを有効にします。
5. Cloud RunのURLに「/login」を付与して管理画面にログインし、パラメータを設定します
6. LINE Developerにログインします：https://account.line.biz/login
7. チャネルを作成し、webhookの宛先にCloud RunのサービスURLを指定します。

## 環境変数
- OPENAI_APIKEY: OpenAI APIのAPIキー。ChatGPTとWhisperで使用する。
- LINE_ACCESS_TOKEN: LINE Messaging APIのアクセストークン。
- SECRET_KEY: DBに保存するメッセージの暗号化と復号化に使用される秘密鍵。
- ADMIN_PASSWORD: 管理者パスワード。
- GOOGLE_API_KEY: GoogleのAPIキー。Web検索と地図検索、画像認識で使用する。
- GOOGLE_CAPI_KEY: Custom Searchの検索エンジンID。Web検索で使用する。

## 注意
このアプリケーションはFlaskベースで作成されています。そのため、任意のウェブサーバー上にデプロイすることが可能ですが、前提としてはGoogle Cloud runでの動作を想定しています。デプロイ方法は使用するウェブサーバーによります。

Google Cloud run以外で動作させる場合はFirestoreとの紐づけが必要になります。

## ライセンス
このプロジェクトはMITライセンスの下でライセンスされています。
