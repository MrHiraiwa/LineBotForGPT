# LineBotForGPT

このリポジトリは、LINE上で動作するPythonベースのチャットボットです。このボットはChatGPT APIを使用して、ユーザからのメッセージに対してレスポンスを生成します。

## セットアップ

以下のステップに従ってセットアップしてください：

1. Google Cloud Runでデプロイします：Google Cloud Consoleでプロジェクトを作成しCloud Run APIを有効にし、本レポジトリを指定してデプロイします。
デプロイの際は以下の環境変数を設定する必要があります。
OPENAI_APIKEY: OpenAI APIのAPIキー。
LINE_ACCESS_TOKEN: LINE Messaging APIのアクセストークン。
SECRET_KEY: メッセージの暗号化と復号化に使用される秘密鍵。
ADMIN_PASSWORD: 管理者パスワード。

2. 同じプロジェクト内でFirestoreを有効にします：左側のナビゲーションメニューで「Firestore」を選択し、Firestoreをプロジェクトで有効にします。

3. データベースを作成します：Firestoreダッシュボードに移動し、「データベースの作成」をクリックします。「ネイティブ」モードを選択します。

4. Cloud RunのURLに「/login」を付与して管理画面にログインしてパラメータを設定します

## 注意

このアプリケーションはFlaskベースで作成されています。そのため、任意のウェブサーバー上にデプロイすることが可能です。が、前提としてはGoogle Cloud runでの動作を想定しています。デプロイ方法は使用するウェブサーバーによります。

Google Cloud run以外で動作させる場合はFireStoreとの紐づけが必要になります。

## ライセンス

このプロジェクトはMITライセンスの下でライセンスされています。
