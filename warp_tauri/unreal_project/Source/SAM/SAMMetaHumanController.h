// Copyright Warp Open. All Rights Reserved.
// MetaHuman controller for hyper-realistic avatar rendering

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "SAMConnection.h"
#include "SAMMetaHumanController.generated.h"

UENUM(BlueprintType)
enum class ESAMEmotion : uint8
{
    Neutral,
    Happy,
    Sad,
    Angry,
    Surprised,
    Flirty,
    Seductive,
    Aroused,
    Ecstasy,
    Thinking,
    Confident
};

UENUM(BlueprintType)
enum class ESAMAnimationState : uint8
{
    Idle,
    Talking,
    Listening,
    Thinking,
    Emotional,
    Intimate,
    Custom
};

/**
 * Main controller for MetaHuman avatar.
 * Handles all facial expressions, body animations, lip sync, and adult content.
 */
UCLASS(BlueprintType, Blueprintable)
class ATLAS_API ASAMMetaHumanController : public AActor
{
    GENERATED_BODY()

public:
    ASAMMetaHumanController();

    // References
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "SAM|References")
    class USkeletalMeshComponent* BodyMesh;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "SAM|References")
    class USkeletalMeshComponent* FaceMesh;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "SAM|References")
    class UGroomComponent* HairGroom;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "SAM|References")
    class UGroomComponent* BeardGroom;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "SAM|References")
    class UGroomComponent* EyebrowGroom;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "SAM|References")
    class UGroomComponent* EyelashGroom;

    // Connection
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "SAM|Connection")
    USAMConnection* Connection;

    // State
    UPROPERTY(BlueprintReadOnly, Category = "SAM|State")
    ESAMAnimationState CurrentState = ESAMAnimationState::Idle;

    UPROPERTY(BlueprintReadOnly, Category = "SAM|State")
    ESAMEmotion CurrentEmotion = ESAMEmotion::Neutral;

    UPROPERTY(BlueprintReadOnly, Category = "SAM|State")
    float ArousalLevel = 0.0f;

    // Idle settings
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "SAM|Idle")
    float BreathingRate = 2.5f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "SAM|Idle")
    float BlinkInterval = 3.0f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "SAM|Idle")
    float IdleMicroMovementIntensity = 0.3f;

    // Facial control
    UFUNCTION(BlueprintCallable, Category = "SAM|Face")
    void SetFacialExpression(ESAMEmotion Emotion, float Intensity = 1.0f, float BlendTime = 0.3f);

    UFUNCTION(BlueprintCallable, Category = "SAM|Face")
    void SetMorphTarget(const FName& MorphName, float Value);

    UFUNCTION(BlueprintCallable, Category = "SAM|Face")
    void SetMultipleMorphTargets(const TMap<FName, float>& MorphTargets);

    UFUNCTION(BlueprintCallable, Category = "SAM|Face")
    void TriggerBlink();

    // Lip sync
    UFUNCTION(BlueprintCallable, Category = "SAM|LipSync")
    void SetViseme(const FName& Viseme, float Weight);

    UFUNCTION(BlueprintCallable, Category = "SAM|LipSync")
    void PlayLipSyncData(const TArray<FSAMLipSyncFrame>& Frames);

    UFUNCTION(BlueprintCallable, Category = "SAM|LipSync")
    void StopLipSync();

    // Body control
    UFUNCTION(BlueprintCallable, Category = "SAM|Body")
    void SetBodyMorphTarget(const FName& MorphName, float Value);

    UFUNCTION(BlueprintCallable, Category = "SAM|Body")
    void ApplyCharacterConfig(const TMap<FName, float>& BodyParams, const TMap<FName, float>& FaceParams);

    // Animation
    UFUNCTION(BlueprintCallable, Category = "SAM|Animation")
    void PlayAnimation(const FName& AnimationName, float BlendTime = 0.2f);

    UFUNCTION(BlueprintCallable, Category = "SAM|Animation")
    void SetAnimationState(ESAMAnimationState NewState);

    // Adult content
    UFUNCTION(BlueprintCallable, Category = "SAM|Adult")
    void SetArousalState(float Level);

    UFUNCTION(BlueprintCallable, Category = "SAM|Adult")
    void PlayIntimateAnimation(const FName& AnimationName, float Speed = 1.0f);

    // Gaze / Look At
    UFUNCTION(BlueprintCallable, Category = "SAM|Gaze")
    void LookAt(const FVector& WorldLocation, float BlendTime = 0.2f);

    UFUNCTION(BlueprintCallable, Category = "SAM|Gaze")
    void LookAtActor(AActor* Target, float BlendTime = 0.2f);

    UFUNCTION(BlueprintCallable, Category = "SAM|Gaze")
    void ResetGaze();

protected:
    virtual void BeginPlay() override;
    virtual void Tick(float DeltaTime) override;

private:
    // Idle behavior
    float BreathingPhase = 0.0f;
    float BlinkTimer = 0.0f;
    float NextBlinkTime = 0.0f;
    bool bIsBlinking = false;

    // Lip sync
    TArray<FSAMLipSyncFrame> LipSyncData;
    int32 CurrentLipSyncFrame = 0;
    float LipSyncStartTime = 0.0f;
    bool bIsPlayingLipSync = false;

    // Target emotion blend
    TMap<FName, float> TargetMorphValues;
    TMap<FName, float> CurrentMorphValues;
    float EmotionBlendTime = 0.0f;
    float EmotionBlendProgress = 0.0f;

    // Gaze
    FVector GazeTarget;
    bool bHasGazeTarget = false;

    void UpdateIdleBehavior(float DeltaTime);
    void UpdateBreathing(float DeltaTime);
    void UpdateBlinking(float DeltaTime);
    void UpdateMicroMovements(float DeltaTime);
    void UpdateLipSync(float DeltaTime);
    void UpdateEmotionBlend(float DeltaTime);
    void UpdateGaze(float DeltaTime);

    void HandleMessage(const FString& Message);
    void ProcessCommand(const TSharedPtr<FJsonObject>& JsonObject);

    // MetaHuman specific morph target mapping
    TMap<FName, FName> WarpToMetaHumanMap;
    void InitializeMorphMapping();
    FName MapToMetaHumanMorph(const FName& WarpMorphName);

    // Emotion presets
    TMap<FName, float> GetEmotionMorphs(ESAMEmotion Emotion, float Intensity);
};

/**
 * Lip sync frame data
 */
USTRUCT(BlueprintType)
struct FSAMLipSyncFrame
{
    GENERATED_BODY()

    UPROPERTY(BlueprintReadWrite)
    float Time = 0.0f;

    UPROPERTY(BlueprintReadWrite)
    FName Viseme;

    UPROPERTY(BlueprintReadWrite)
    float Intensity = 1.0f;
};
