// Copyright Warp Open. All Rights Reserved.

using UnrealBuildTool;

public class SAM : ModuleRules
{
    public SAM(ReadOnlyTargetRules Target) : base(Target)
    {
        PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;

        PublicDependencyModuleNames.AddRange(new string[] {
            "Core",
            "CoreUObject",
            "Engine",
            "InputCore",
            "WebSockets",
            "Json",
            "JsonUtilities",
            "HTTP",
            "ControlRig",
            "IKRig",
            "AnimGraphRuntime",
            "LiveLinkInterface",
            "LiveLinkAnimationCore"
        });

        PrivateDependencyModuleNames.AddRange(new string[] {
            "Slate",
            "SlateCore",
            "UMG"
        });

        // Enable IWYU
        bEnforceIWYU = true;
    }
}
