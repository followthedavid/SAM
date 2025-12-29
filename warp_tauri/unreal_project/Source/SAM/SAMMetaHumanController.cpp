// Copyright Warp Open. All Rights Reserved.

#include "SAMMetaHumanController.h"
#include "Components/SkeletalMeshComponent.h"
#include "GroomComponent.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"

ASAMMetaHumanController::ASAMMetaHumanController()
{
    PrimaryActorTick.bCanEverTick = true;

    // Create connection component
    Connection = CreateDefaultSubobject<USAMConnection>(TEXT("SAMConnection"));
}

void ASAMMetaHumanController::BeginPlay()
{
    Super::BeginPlay();

    InitializeMorphMapping();

    // Bind to connection events
    if (Connection)
    {
        Connection->OnMessageReceived.AddDynamic(this, &ASAMMetaHumanController::HandleMessage);
    }

    // Initialize blink timer
    NextBlinkTime = FMath::RandRange(BlinkInterval * 0.5f, BlinkInterval * 1.5f);

    UE_LOG(LogTemp, Log, TEXT("[SAM] MetaHuman Controller initialized"));
}

void ASAMMetaHumanController::Tick(float DeltaTime)
{
    Super::Tick(DeltaTime);

    UpdateIdleBehavior(DeltaTime);
    UpdateLipSync(DeltaTime);
    UpdateEmotionBlend(DeltaTime);
    UpdateGaze(DeltaTime);
}

void ASAMMetaHumanController::InitializeMorphMapping()
{
    // Map Warp Open morph names to MetaHuman FACS-based morph targets
    // MetaHuman uses Apple ARKit compatible naming

    // Face shape
    WarpToMetaHumanMap.Add(TEXT("face_jawWidth"), TEXT("jawOpen"));
    WarpToMetaHumanMap.Add(TEXT("face_mouthOpen"), TEXT("jawOpen"));
    WarpToMetaHumanMap.Add(TEXT("face_smile"), TEXT("mouthSmile_L"));  // Need both L and R
    WarpToMetaHumanMap.Add(TEXT("face_frown"), TEXT("mouthFrown_L"));
    WarpToMetaHumanMap.Add(TEXT("face_eyesClosed"), TEXT("eyeBlink_L"));

    // Brows
    WarpToMetaHumanMap.Add(TEXT("face_browRaise"), TEXT("browOuterUp_L"));
    WarpToMetaHumanMap.Add(TEXT("face_browFurrow"), TEXT("browDown_L"));

    // Eyes
    WarpToMetaHumanMap.Add(TEXT("face_eyeSquint"), TEXT("eyeSquint_L"));
    WarpToMetaHumanMap.Add(TEXT("face_eyeWide"), TEXT("eyeWide_L"));

    // Mouth
    WarpToMetaHumanMap.Add(TEXT("face_mouthPucker"), TEXT("mouthPucker"));
    WarpToMetaHumanMap.Add(TEXT("face_mouthFunnel"), TEXT("mouthFunnel"));

    // Visemes (ARKit compatible)
    WarpToMetaHumanMap.Add(TEXT("face_viseme_A"), TEXT("viseme_aa"));
    WarpToMetaHumanMap.Add(TEXT("face_viseme_E"), TEXT("viseme_E"));
    WarpToMetaHumanMap.Add(TEXT("face_viseme_I"), TEXT("viseme_I"));
    WarpToMetaHumanMap.Add(TEXT("face_viseme_O"), TEXT("viseme_O"));
    WarpToMetaHumanMap.Add(TEXT("face_viseme_U"), TEXT("viseme_U"));
    WarpToMetaHumanMap.Add(TEXT("face_viseme_M"), TEXT("viseme_PP"));
    WarpToMetaHumanMap.Add(TEXT("face_viseme_F"), TEXT("viseme_FF"));
    WarpToMetaHumanMap.Add(TEXT("face_viseme_TH"), TEXT("viseme_TH"));
    WarpToMetaHumanMap.Add(TEXT("face_viseme_S"), TEXT("viseme_SS"));
    WarpToMetaHumanMap.Add(TEXT("face_viseme_K"), TEXT("viseme_kk"));
    WarpToMetaHumanMap.Add(TEXT("face_viseme_R"), TEXT("viseme_RR"));

    UE_LOG(LogTemp, Log, TEXT("[SAM] Initialized %d morph mappings"), WarpToMetaHumanMap.Num());
}

FName ASAMMetaHumanController::MapToMetaHumanMorph(const FName& WarpMorphName)
{
    if (const FName* Found = WarpToMetaHumanMap.Find(WarpMorphName))
    {
        return *Found;
    }
    return WarpMorphName; // Return as-is if no mapping
}

void ASAMMetaHumanController::HandleMessage(const FString& Message)
{
    TSharedPtr<FJsonObject> JsonObject;
    TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(Message);

    if (FJsonSerializer::Deserialize(Reader, JsonObject) && JsonObject.IsValid())
    {
        ProcessCommand(JsonObject);
    }
}

void ASAMMetaHumanController::ProcessCommand(const TSharedPtr<FJsonObject>& JsonObject)
{
    FString Type;
    if (!JsonObject->TryGetStringField(TEXT("type"), Type))
    {
        return;
    }

    if (Type == TEXT("emotion"))
    {
        FString Emotion;
        float Intensity = 1.0f;
        JsonObject->TryGetStringField(TEXT("emotion"), Emotion);
        JsonObject->TryGetNumberField(TEXT("intensity"), Intensity);

        // Map string to enum
        ESAMEmotion EmotionEnum = ESAMEmotion::Neutral;
        if (Emotion == TEXT("happy")) EmotionEnum = ESAMEmotion::Happy;
        else if (Emotion == TEXT("sad")) EmotionEnum = ESAMEmotion::Sad;
        else if (Emotion == TEXT("angry")) EmotionEnum = ESAMEmotion::Angry;
        else if (Emotion == TEXT("surprised")) EmotionEnum = ESAMEmotion::Surprised;
        else if (Emotion == TEXT("flirty")) EmotionEnum = ESAMEmotion::Flirty;
        else if (Emotion == TEXT("seductive")) EmotionEnum = ESAMEmotion::Seductive;
        else if (Emotion == TEXT("aroused")) EmotionEnum = ESAMEmotion::Aroused;
        else if (Emotion == TEXT("ecstasy")) EmotionEnum = ESAMEmotion::Ecstasy;
        else if (Emotion == TEXT("thinking")) EmotionEnum = ESAMEmotion::Thinking;
        else if (Emotion == TEXT("confident")) EmotionEnum = ESAMEmotion::Confident;

        SetFacialExpression(EmotionEnum, Intensity);
    }
    else if (Type == TEXT("morph"))
    {
        const TSharedPtr<FJsonObject>* MorphTargets;
        if (JsonObject->TryGetObjectField(TEXT("morph_targets"), MorphTargets))
        {
            TMap<FName, float> Morphs;
            for (const auto& Pair : (*MorphTargets)->Values)
            {
                double Value;
                if (Pair.Value->TryGetNumber(Value))
                {
                    Morphs.Add(FName(*Pair.Key), static_cast<float>(Value));
                }
            }
            SetMultipleMorphTargets(Morphs);
        }
    }
    else if (Type == TEXT("animation"))
    {
        FString Animation;
        if (JsonObject->TryGetStringField(TEXT("animation"), Animation))
        {
            PlayAnimation(FName(*Animation));
        }
    }
    else if (Type == TEXT("lipsync"))
    {
        const TArray<TSharedPtr<FJsonValue>>* DataArray;
        if (JsonObject->TryGetArrayField(TEXT("data"), DataArray))
        {
            TArray<FSAMLipSyncFrame> Frames;
            for (const auto& Item : *DataArray)
            {
                const TSharedPtr<FJsonObject>* FrameObj;
                if (Item->TryGetObject(FrameObj))
                {
                    FSAMLipSyncFrame Frame;
                    (*FrameObj)->TryGetNumberField(TEXT("time"), Frame.Time);
                    FString Viseme;
                    if ((*FrameObj)->TryGetStringField(TEXT("viseme"), Viseme))
                    {
                        Frame.Viseme = FName(*Viseme);
                    }
                    (*FrameObj)->TryGetNumberField(TEXT("intensity"), Frame.Intensity);
                    Frames.Add(Frame);
                }
            }
            PlayLipSyncData(Frames);
        }
    }
    else if (Type == TEXT("arousal"))
    {
        float Level;
        if (JsonObject->TryGetNumberField(TEXT("level"), Level))
        {
            SetArousalState(Level);
        }
    }
    else if (Type == TEXT("look_at"))
    {
        const TSharedPtr<FJsonObject>* Target;
        if (JsonObject->TryGetObjectField(TEXT("target"), Target))
        {
            double X, Y, Z;
            (*Target)->TryGetNumberField(TEXT("x"), X);
            (*Target)->TryGetNumberField(TEXT("y"), Y);
            (*Target)->TryGetNumberField(TEXT("z"), Z);
            LookAt(FVector(X, Y, Z));
        }
    }
}

void ASAMMetaHumanController::UpdateIdleBehavior(float DeltaTime)
{
    if (CurrentState == ESAMAnimationState::Idle || CurrentState == ESAMAnimationState::Listening)
    {
        UpdateBreathing(DeltaTime);
        UpdateBlinking(DeltaTime);
        UpdateMicroMovements(DeltaTime);
    }
}

void ASAMMetaHumanController::UpdateBreathing(float DeltaTime)
{
    BreathingPhase += DeltaTime * BreathingRate;
    float BreathValue = (FMath::Sin(BreathingPhase) + 1.0f) * 0.5f;

    // Apply subtle chest/torso movement via morph or bone
    if (BodyMesh)
    {
        // MetaHuman uses bone transforms for breathing
        // This would be handled by the Animation Blueprint
    }
}

void ASAMMetaHumanController::UpdateBlinking(float DeltaTime)
{
    BlinkTimer += DeltaTime;

    if (!bIsBlinking && BlinkTimer >= NextBlinkTime)
    {
        TriggerBlink();
    }
}

void ASAMMetaHumanController::TriggerBlink()
{
    bIsBlinking = true;
    BlinkTimer = 0.0f;
    NextBlinkTime = FMath::RandRange(BlinkInterval * 0.5f, BlinkInterval * 1.5f);

    // Animate blink using morph targets
    // In production, this would be a timeline or curve
    if (FaceMesh)
    {
        // Quick blink - set to 1, then back to 0
        SetMorphTarget(TEXT("eyeBlink_L"), 1.0f);
        SetMorphTarget(TEXT("eyeBlink_R"), 1.0f);

        // Schedule return to 0 (in production use timer or timeline)
        FTimerHandle BlinkHandle;
        GetWorld()->GetTimerManager().SetTimer(BlinkHandle, [this]()
        {
            SetMorphTarget(TEXT("eyeBlink_L"), 0.0f);
            SetMorphTarget(TEXT("eyeBlink_R"), 0.0f);
            bIsBlinking = false;
        }, 0.15f, false);
    }
}

void ASAMMetaHumanController::UpdateMicroMovements(float DeltaTime)
{
    float Time = GetWorld()->GetTimeSeconds();

    // Subtle head movement
    float HeadTilt = FMath::Sin(Time * 0.3f) * IdleMicroMovementIntensity * 2.0f;
    float HeadTurn = FMath::Sin(Time * 0.2f + 1.0f) * IdleMicroMovementIntensity * 1.5f;

    // Apply via control rig or bone transforms
    // This is typically done in the Animation Blueprint for MetaHuman
}

void ASAMMetaHumanController::SetFacialExpression(ESAMEmotion Emotion, float Intensity, float BlendTime)
{
    CurrentEmotion = Emotion;
    TargetMorphValues = GetEmotionMorphs(Emotion, Intensity);
    EmotionBlendTime = BlendTime;
    EmotionBlendProgress = 0.0f;
}

TMap<FName, float> ASAMMetaHumanController::GetEmotionMorphs(ESAMEmotion Emotion, float Intensity)
{
    TMap<FName, float> Morphs;

    switch (Emotion)
    {
    case ESAMEmotion::Happy:
        Morphs.Add(TEXT("mouthSmile_L"), 0.8f * Intensity);
        Morphs.Add(TEXT("mouthSmile_R"), 0.8f * Intensity);
        Morphs.Add(TEXT("cheekSquint_L"), 0.3f * Intensity);
        Morphs.Add(TEXT("cheekSquint_R"), 0.3f * Intensity);
        Morphs.Add(TEXT("eyeSquint_L"), 0.2f * Intensity);
        Morphs.Add(TEXT("eyeSquint_R"), 0.2f * Intensity);
        break;

    case ESAMEmotion::Flirty:
        Morphs.Add(TEXT("mouthSmile_L"), 0.4f * Intensity);
        Morphs.Add(TEXT("mouthSmile_R"), 0.6f * Intensity); // Asymmetric smirk
        Morphs.Add(TEXT("browOuterUp_L"), 0.3f * Intensity);
        Morphs.Add(TEXT("eyeSquint_R"), 0.2f * Intensity);
        break;

    case ESAMEmotion::Seductive:
        Morphs.Add(TEXT("mouthSmile_L"), 0.3f * Intensity);
        Morphs.Add(TEXT("mouthSmile_R"), 0.4f * Intensity);
        Morphs.Add(TEXT("eyeSquint_L"), 0.3f * Intensity);
        Morphs.Add(TEXT("eyeSquint_R"), 0.3f * Intensity);
        Morphs.Add(TEXT("jawOpen"), 0.05f * Intensity);
        Morphs.Add(TEXT("mouthPucker"), 0.1f * Intensity);
        break;

    case ESAMEmotion::Aroused:
        Morphs.Add(TEXT("eyeSquint_L"), 0.2f * Intensity);
        Morphs.Add(TEXT("eyeSquint_R"), 0.2f * Intensity);
        Morphs.Add(TEXT("jawOpen"), 0.15f * Intensity);
        Morphs.Add(TEXT("mouthClose"), -0.1f * Intensity);
        break;

    case ESAMEmotion::Ecstasy:
        Morphs.Add(TEXT("eyeBlink_L"), 0.7f * Intensity);
        Morphs.Add(TEXT("eyeBlink_R"), 0.7f * Intensity);
        Morphs.Add(TEXT("jawOpen"), 0.4f * Intensity);
        Morphs.Add(TEXT("browInnerUp"), 0.5f * Intensity);
        Morphs.Add(TEXT("mouthStretch_L"), 0.2f * Intensity);
        Morphs.Add(TEXT("mouthStretch_R"), 0.2f * Intensity);
        break;

    case ESAMEmotion::Thinking:
        Morphs.Add(TEXT("browDown_L"), 0.2f * Intensity);
        Morphs.Add(TEXT("browDown_R"), 0.2f * Intensity);
        Morphs.Add(TEXT("eyeSquint_L"), 0.15f * Intensity);
        Morphs.Add(TEXT("eyeSquint_R"), 0.15f * Intensity);
        Morphs.Add(TEXT("mouthPucker"), 0.1f * Intensity);
        break;

    case ESAMEmotion::Confident:
        Morphs.Add(TEXT("mouthSmile_L"), 0.3f * Intensity);
        Morphs.Add(TEXT("mouthSmile_R"), 0.3f * Intensity);
        Morphs.Add(TEXT("browOuterUp_L"), 0.15f * Intensity);
        Morphs.Add(TEXT("browOuterUp_R"), 0.15f * Intensity);
        Morphs.Add(TEXT("noseSneer_L"), 0.05f * Intensity);
        Morphs.Add(TEXT("noseSneer_R"), 0.05f * Intensity);
        break;

    case ESAMEmotion::Sad:
        Morphs.Add(TEXT("mouthFrown_L"), 0.5f * Intensity);
        Morphs.Add(TEXT("mouthFrown_R"), 0.5f * Intensity);
        Morphs.Add(TEXT("browInnerUp"), 0.4f * Intensity);
        Morphs.Add(TEXT("eyeSquint_L"), 0.1f * Intensity);
        Morphs.Add(TEXT("eyeSquint_R"), 0.1f * Intensity);
        break;

    case ESAMEmotion::Angry:
        Morphs.Add(TEXT("browDown_L"), 0.7f * Intensity);
        Morphs.Add(TEXT("browDown_R"), 0.7f * Intensity);
        Morphs.Add(TEXT("eyeSquint_L"), 0.3f * Intensity);
        Morphs.Add(TEXT("eyeSquint_R"), 0.3f * Intensity);
        Morphs.Add(TEXT("noseSneer_L"), 0.3f * Intensity);
        Morphs.Add(TEXT("noseSneer_R"), 0.3f * Intensity);
        Morphs.Add(TEXT("jawForward"), 0.2f * Intensity);
        break;

    case ESAMEmotion::Surprised:
        Morphs.Add(TEXT("browOuterUp_L"), 0.8f * Intensity);
        Morphs.Add(TEXT("browOuterUp_R"), 0.8f * Intensity);
        Morphs.Add(TEXT("browInnerUp"), 0.6f * Intensity);
        Morphs.Add(TEXT("eyeWide_L"), 0.5f * Intensity);
        Morphs.Add(TEXT("eyeWide_R"), 0.5f * Intensity);
        Morphs.Add(TEXT("jawOpen"), 0.3f * Intensity);
        break;

    default:
        // Neutral - reset all
        break;
    }

    return Morphs;
}

void ASAMMetaHumanController::UpdateEmotionBlend(float DeltaTime)
{
    if (EmotionBlendProgress < 1.0f && EmotionBlendTime > 0.0f)
    {
        EmotionBlendProgress += DeltaTime / EmotionBlendTime;
        EmotionBlendProgress = FMath::Clamp(EmotionBlendProgress, 0.0f, 1.0f);

        // Blend towards target morphs
        for (const auto& Target : TargetMorphValues)
        {
            float* Current = CurrentMorphValues.Find(Target.Key);
            float CurrentValue = Current ? *Current : 0.0f;
            float BlendedValue = FMath::Lerp(CurrentValue, Target.Value, EmotionBlendProgress);

            SetMorphTarget(Target.Key, BlendedValue);
            CurrentMorphValues.Add(Target.Key, BlendedValue);
        }
    }
}

void ASAMMetaHumanController::SetMorphTarget(const FName& MorphName, float Value)
{
    if (FaceMesh && FaceMesh->GetSkeletalMeshAsset())
    {
        FaceMesh->SetMorphTarget(MorphName, Value);
    }
}

void ASAMMetaHumanController::SetMultipleMorphTargets(const TMap<FName, float>& MorphTargets)
{
    for (const auto& Pair : MorphTargets)
    {
        FName MappedName = MapToMetaHumanMorph(Pair.Key);
        SetMorphTarget(MappedName, Pair.Value);
    }
}

void ASAMMetaHumanController::SetViseme(const FName& Viseme, float Weight)
{
    FName MappedViseme = MapToMetaHumanMorph(Viseme);
    SetMorphTarget(MappedViseme, Weight);
}

void ASAMMetaHumanController::PlayLipSyncData(const TArray<FSAMLipSyncFrame>& Frames)
{
    LipSyncData = Frames;
    CurrentLipSyncFrame = 0;
    LipSyncStartTime = GetWorld()->GetTimeSeconds();
    bIsPlayingLipSync = true;

    UE_LOG(LogTemp, Log, TEXT("[SAM] Playing lip sync with %d frames"), Frames.Num());
}

void ASAMMetaHumanController::StopLipSync()
{
    bIsPlayingLipSync = false;
    LipSyncData.Empty();

    // Reset to neutral mouth
    SetViseme(TEXT("face_viseme_REST"), 1.0f);
}

void ASAMMetaHumanController::UpdateLipSync(float DeltaTime)
{
    if (!bIsPlayingLipSync || LipSyncData.Num() == 0) return;

    float CurrentTime = (GetWorld()->GetTimeSeconds() - LipSyncStartTime) * 1000.0f; // Convert to ms

    // Process frames up to current time
    while (CurrentLipSyncFrame < LipSyncData.Num())
    {
        const FSAMLipSyncFrame& Frame = LipSyncData[CurrentLipSyncFrame];

        if (Frame.Time <= CurrentTime)
        {
            SetViseme(Frame.Viseme, Frame.Intensity);
            CurrentLipSyncFrame++;
        }
        else
        {
            break;
        }
    }

    // Check if finished
    if (CurrentLipSyncFrame >= LipSyncData.Num())
    {
        StopLipSync();
    }
}

void ASAMMetaHumanController::SetBodyMorphTarget(const FName& MorphName, float Value)
{
    if (BodyMesh && BodyMesh->GetSkeletalMeshAsset())
    {
        BodyMesh->SetMorphTarget(MorphName, Value);
    }
}

void ASAMMetaHumanController::ApplyCharacterConfig(const TMap<FName, float>& BodyParams, const TMap<FName, float>& FaceParams)
{
    for (const auto& Pair : BodyParams)
    {
        SetBodyMorphTarget(Pair.Key, Pair.Value);
    }

    for (const auto& Pair : FaceParams)
    {
        SetMorphTarget(Pair.Key, Pair.Value);
    }

    UE_LOG(LogTemp, Log, TEXT("[SAM] Applied character config: %d body, %d face params"),
        BodyParams.Num(), FaceParams.Num());
}

void ASAMMetaHumanController::PlayAnimation(const FName& AnimationName, float BlendTime)
{
    // This would trigger animations via the Animation Blueprint
    UE_LOG(LogTemp, Log, TEXT("[SAM] Playing animation: %s"), *AnimationName.ToString());
}

void ASAMMetaHumanController::SetAnimationState(ESAMAnimationState NewState)
{
    CurrentState = NewState;

    if (Connection)
    {
        FString StateString;
        switch (NewState)
        {
        case ESAMAnimationState::Idle: StateString = TEXT("idle"); break;
        case ESAMAnimationState::Talking: StateString = TEXT("talking"); break;
        case ESAMAnimationState::Listening: StateString = TEXT("listening"); break;
        case ESAMAnimationState::Thinking: StateString = TEXT("thinking"); break;
        case ESAMAnimationState::Emotional: StateString = TEXT("emotional"); break;
        case ESAMAnimationState::Intimate: StateString = TEXT("intimate"); break;
        default: StateString = TEXT("custom"); break;
        }

        Connection->SendStateChange(StateString, TEXT(""));
    }
}

void ASAMMetaHumanController::SetArousalState(float Level)
{
    ArousalLevel = FMath::Clamp(Level, 0.0f, 1.0f);

    // Apply subtle expression changes
    if (Level > 0.3f)
    {
        SetFacialExpression(ESAMEmotion::Aroused, Level);
    }

    // Notify connection
    if (Connection)
    {
        Connection->SendArousalState(ArousalLevel);
    }
}

void ASAMMetaHumanController::PlayIntimateAnimation(const FName& AnimationName, float Speed)
{
    SetAnimationState(ESAMAnimationState::Intimate);
    PlayAnimation(AnimationName);

    UE_LOG(LogTemp, Log, TEXT("[SAM] Playing intimate animation: %s @ %.1fx"), *AnimationName.ToString(), Speed);
}

void ASAMMetaHumanController::LookAt(const FVector& WorldLocation, float BlendTime)
{
    GazeTarget = WorldLocation;
    bHasGazeTarget = true;

    // Eye look-at is typically handled by the Control Rig in MetaHuman
    UE_LOG(LogTemp, Verbose, TEXT("[SAM] Looking at: %s"), *WorldLocation.ToString());
}

void ASAMMetaHumanController::LookAtActor(AActor* Target, float BlendTime)
{
    if (Target)
    {
        LookAt(Target->GetActorLocation(), BlendTime);
    }
}

void ASAMMetaHumanController::ResetGaze()
{
    bHasGazeTarget = false;
}

void ASAMMetaHumanController::UpdateGaze(float DeltaTime)
{
    // Gaze updates are handled by the Control Rig in the Animation Blueprint
    // This would set the eye look-at target via the rig
}
