// Copyright Warp Open. All Rights Reserved.
// WebSocket connection to Warp Open terminal

#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "IWebSocket.h"
#include "SAMConnection.generated.h"

DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FOnSAMMessageReceived, const FString&, Message);
DECLARE_DYNAMIC_MULTICAST_DELEGATE(FOnSAMConnected);
DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FOnSAMDisconnected, const FString&, Reason);

/**
 * WebSocket connection component for communicating with Warp Open terminal.
 * Handles all real-time avatar commands: morphs, animations, emotions, lip sync.
 */
UCLASS(ClassGroup=(SAM), meta=(BlueprintSpawnableComponent))
class ATLAS_API USAMConnection : public UActorComponent
{
    GENERATED_BODY()

public:
    USAMConnection();

    // Connection settings
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "SAM|Connection")
    FString ServerURL = TEXT("ws://localhost:8765");

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "SAM|Connection")
    bool bAutoConnect = true;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "SAM|Connection")
    float ReconnectDelay = 3.0f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "SAM|Connection")
    int32 MaxReconnectAttempts = 10;

    // State
    UPROPERTY(BlueprintReadOnly, Category = "SAM|Connection")
    bool bIsConnected = false;

    // Events
    UPROPERTY(BlueprintAssignable, Category = "SAM|Events")
    FOnSAMMessageReceived OnMessageReceived;

    UPROPERTY(BlueprintAssignable, Category = "SAM|Events")
    FOnSAMConnected OnConnected;

    UPROPERTY(BlueprintAssignable, Category = "SAM|Events")
    FOnSAMDisconnected OnDisconnected;

    // Methods
    UFUNCTION(BlueprintCallable, Category = "SAM|Connection")
    void Connect();

    UFUNCTION(BlueprintCallable, Category = "SAM|Connection")
    void Disconnect();

    UFUNCTION(BlueprintCallable, Category = "SAM|Connection")
    void SendMessage(const FString& Message);

    UFUNCTION(BlueprintCallable, Category = "SAM|Connection")
    void SendEvent(const FString& EventType, const FString& Data);

    // Send typed messages
    UFUNCTION(BlueprintCallable, Category = "SAM|Messages")
    void SendStateChange(const FString& Animation, const FString& Emotion);

    UFUNCTION(BlueprintCallable, Category = "SAM|Messages")
    void SendUserGesture(const FString& Gesture);

    UFUNCTION(BlueprintCallable, Category = "SAM|Messages")
    void SendArousalState(float Level);

protected:
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;
    virtual void TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction) override;

private:
    TSharedPtr<IWebSocket> WebSocket;
    int32 ReconnectAttempts = 0;
    float ReconnectTimer = 0.0f;
    bool bShouldReconnect = false;

    void SetupWebSocket();
    void HandleConnected();
    void HandleConnectionError(const FString& Error);
    void HandleClosed(int32 StatusCode, const FString& Reason, bool bWasClean);
    void HandleMessage(const FString& Message);
    void AttemptReconnect(float DeltaTime);
};
