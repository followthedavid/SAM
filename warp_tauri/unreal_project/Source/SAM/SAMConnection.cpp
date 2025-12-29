// Copyright Warp Open. All Rights Reserved.

#include "SAMConnection.h"
#include "WebSocketsModule.h"
#include "IWebSocket.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/JsonWriter.h"

USAMConnection::USAMConnection()
{
    PrimaryComponentTick.bCanEverTick = true;
    PrimaryComponentTick.bStartWithTickEnabled = true;
}

void USAMConnection::BeginPlay()
{
    Super::BeginPlay();

    if (bAutoConnect)
    {
        Connect();
    }
}

void USAMConnection::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
    Super::EndPlay(EndPlayReason);
    Disconnect();
}

void USAMConnection::TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction)
{
    Super::TickComponent(DeltaTime, TickType, ThisTickFunction);

    if (bShouldReconnect && !bIsConnected)
    {
        AttemptReconnect(DeltaTime);
    }
}

void USAMConnection::Connect()
{
    if (bIsConnected && WebSocket.IsValid() && WebSocket->IsConnected())
    {
        UE_LOG(LogTemp, Warning, TEXT("[SAM] Already connected"));
        return;
    }

    ReconnectAttempts = 0;
    bShouldReconnect = true;
    SetupWebSocket();
}

void USAMConnection::SetupWebSocket()
{
    if (!FModuleManager::Get().IsModuleLoaded("WebSockets"))
    {
        FModuleManager::Get().LoadModule("WebSockets");
    }

    WebSocket = FWebSocketsModule::Get().CreateWebSocket(ServerURL, TEXT("ws"));

    WebSocket->OnConnected().AddLambda([this]()
    {
        HandleConnected();
    });

    WebSocket->OnConnectionError().AddLambda([this](const FString& Error)
    {
        HandleConnectionError(Error);
    });

    WebSocket->OnClosed().AddLambda([this](int32 StatusCode, const FString& Reason, bool bWasClean)
    {
        HandleClosed(StatusCode, Reason, bWasClean);
    });

    WebSocket->OnMessage().AddLambda([this](const FString& Message)
    {
        HandleMessage(Message);
    });

    UE_LOG(LogTemp, Log, TEXT("[SAM] Connecting to %s..."), *ServerURL);
    WebSocket->Connect();
}

void USAMConnection::Disconnect()
{
    bShouldReconnect = false;

    if (WebSocket.IsValid())
    {
        WebSocket->Close();
        WebSocket.Reset();
    }

    bIsConnected = false;
}

void USAMConnection::HandleConnected()
{
    bIsConnected = true;
    ReconnectAttempts = 0;
    UE_LOG(LogTemp, Log, TEXT("[SAM] Connected to Warp Open"));

    // Register with server
    TSharedPtr<FJsonObject> JsonObject = MakeShareable(new FJsonObject);
    JsonObject->SetStringField(TEXT("type"), TEXT("register"));
    JsonObject->SetStringField(TEXT("client_type"), TEXT("unreal_metahuman"));
    JsonObject->SetStringField(TEXT("version"), TEXT("2.0"));

    TArray<TSharedPtr<FJsonValue>> Capabilities;
    Capabilities.Add(MakeShareable(new FJsonValueString(TEXT("metahuman"))));
    Capabilities.Add(MakeShareable(new FJsonValueString(TEXT("lumen"))));
    Capabilities.Add(MakeShareable(new FJsonValueString(TEXT("nanite"))));
    Capabilities.Add(MakeShareable(new FJsonValueString(TEXT("hair_strands"))));
    Capabilities.Add(MakeShareable(new FJsonValueString(TEXT("livelink"))));
    Capabilities.Add(MakeShareable(new FJsonValueString(TEXT("full_body_ik"))));
    JsonObject->SetArrayField(TEXT("capabilities"), Capabilities);

    FString OutputString;
    TSharedRef<TJsonWriter<>> Writer = TJsonWriterFactory<>::Create(&OutputString);
    FJsonSerializer::Serialize(JsonObject.ToSharedRef(), Writer);

    SendMessage(OutputString);

    OnConnected.Broadcast();
}

void USAMConnection::HandleConnectionError(const FString& Error)
{
    UE_LOG(LogTemp, Warning, TEXT("[SAM] Connection error: %s"), *Error);
    bIsConnected = false;
}

void USAMConnection::HandleClosed(int32 StatusCode, const FString& Reason, bool bWasClean)
{
    UE_LOG(LogTemp, Log, TEXT("[SAM] Connection closed: %s (Code: %d)"), *Reason, StatusCode);
    bIsConnected = false;
    OnDisconnected.Broadcast(Reason);
}

void USAMConnection::HandleMessage(const FString& Message)
{
    UE_LOG(LogTemp, Verbose, TEXT("[SAM] Received: %s"), *Message);
    OnMessageReceived.Broadcast(Message);
}

void USAMConnection::AttemptReconnect(float DeltaTime)
{
    ReconnectTimer -= DeltaTime;

    if (ReconnectTimer <= 0.0f)
    {
        if (ReconnectAttempts < MaxReconnectAttempts)
        {
            ReconnectAttempts++;
            UE_LOG(LogTemp, Log, TEXT("[SAM] Reconnection attempt %d/%d"), ReconnectAttempts, MaxReconnectAttempts);
            SetupWebSocket();
            ReconnectTimer = ReconnectDelay;
        }
        else
        {
            UE_LOG(LogTemp, Warning, TEXT("[SAM] Max reconnection attempts reached"));
            bShouldReconnect = false;
        }
    }
}

void USAMConnection::SendMessage(const FString& Message)
{
    if (WebSocket.IsValid() && bIsConnected)
    {
        WebSocket->Send(Message);
        UE_LOG(LogTemp, Verbose, TEXT("[SAM] Sent: %s"), *Message);
    }
}

void USAMConnection::SendEvent(const FString& EventType, const FString& Data)
{
    TSharedPtr<FJsonObject> JsonObject = MakeShareable(new FJsonObject);
    JsonObject->SetStringField(TEXT("type"), TEXT("event"));
    JsonObject->SetStringField(TEXT("event_type"), EventType);
    JsonObject->SetStringField(TEXT("data"), Data);

    FString OutputString;
    TSharedRef<TJsonWriter<>> Writer = TJsonWriterFactory<>::Create(&OutputString);
    FJsonSerializer::Serialize(JsonObject.ToSharedRef(), Writer);

    SendMessage(OutputString);
}

void USAMConnection::SendStateChange(const FString& Animation, const FString& Emotion)
{
    TSharedPtr<FJsonObject> JsonObject = MakeShareable(new FJsonObject);
    JsonObject->SetStringField(TEXT("type"), TEXT("state_change"));

    TSharedPtr<FJsonObject> DataObject = MakeShareable(new FJsonObject);
    DataObject->SetStringField(TEXT("animation"), Animation);
    DataObject->SetStringField(TEXT("emotion"), Emotion);
    JsonObject->SetObjectField(TEXT("data"), DataObject);

    FString OutputString;
    TSharedRef<TJsonWriter<>> Writer = TJsonWriterFactory<>::Create(&OutputString);
    FJsonSerializer::Serialize(JsonObject.ToSharedRef(), Writer);

    SendMessage(OutputString);
}

void USAMConnection::SendUserGesture(const FString& Gesture)
{
    TSharedPtr<FJsonObject> JsonObject = MakeShareable(new FJsonObject);
    JsonObject->SetStringField(TEXT("type"), TEXT("user_gesture"));

    TSharedPtr<FJsonObject> DataObject = MakeShareable(new FJsonObject);
    DataObject->SetStringField(TEXT("gesture"), Gesture);
    JsonObject->SetObjectField(TEXT("data"), DataObject);

    FString OutputString;
    TSharedRef<TJsonWriter<>> Writer = TJsonWriterFactory<>::Create(&OutputString);
    FJsonSerializer::Serialize(JsonObject.ToSharedRef(), Writer);

    SendMessage(OutputString);
}

void USAMConnection::SendArousalState(float Level)
{
    TSharedPtr<FJsonObject> JsonObject = MakeShareable(new FJsonObject);
    JsonObject->SetStringField(TEXT("type"), TEXT("arousal_state"));
    JsonObject->SetNumberField(TEXT("level"), FMath::Clamp(Level, 0.0f, 1.0f));

    FString OutputString;
    TSharedRef<TJsonWriter<>> Writer = TJsonWriterFactory<>::Create(&OutputString);
    FJsonSerializer::Serialize(JsonObject.ToSharedRef(), Writer);

    SendMessage(OutputString);
}
