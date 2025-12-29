// Subsurface Scattering Skin Shader for SAM Avatar
// Provides realistic skin rendering with light transmission

Shader "SAM/Skin SSS"
{
    Properties
    {
        _MainTex ("Albedo (RGB)", 2D) = "white" {}
        _Color ("Color Tint", Color) = (1,1,1,1)

        [Header(Normal)]
        _BumpMap ("Normal Map", 2D) = "bump" {}
        _BumpScale ("Normal Strength", Range(0, 2)) = 1

        [Header(Detail Normal)]
        _DetailNormalMap ("Detail Normal", 2D) = "bump" {}
        _DetailNormalScale ("Detail Normal Strength", Range(0, 2)) = 0.5
        _DetailTiling ("Detail Tiling", Range(1, 50)) = 10

        [Header(Subsurface Scattering)]
        _SSSColor ("SSS Color", Color) = (1, 0.4, 0.25, 1)
        _SSSPower ("SSS Power", Range(0, 5)) = 1.5
        _SSSDistortion ("SSS Distortion", Range(0, 1)) = 0.5
        _SSSScale ("SSS Scale", Range(0, 2)) = 1
        _SSSAmbient ("SSS Ambient", Range(0, 1)) = 0.2

        [Header(Specular)]
        _Smoothness ("Smoothness", Range(0, 1)) = 0.4
        _SpecColor ("Specular Color", Color) = (0.2, 0.2, 0.2, 1)
        _FresnelPower ("Fresnel Power", Range(0, 5)) = 3

        [Header(Ambient Occlusion)]
        _OcclusionMap ("Occlusion Map", 2D) = "white" {}
        _OcclusionStrength ("Occlusion Strength", Range(0, 1)) = 1

        [Header(Thickness)]
        _ThicknessMap ("Thickness Map", 2D) = "white" {}
        _ThicknessScale ("Thickness Scale", Range(0, 2)) = 1
    }

    SubShader
    {
        Tags { "RenderType"="Opaque" "Queue"="Geometry" }
        LOD 300

        CGPROGRAM
        #pragma surface surf SkinSSS fullforwardshadows
        #pragma target 3.0

        sampler2D _MainTex;
        sampler2D _BumpMap;
        sampler2D _DetailNormalMap;
        sampler2D _OcclusionMap;
        sampler2D _ThicknessMap;

        float4 _Color;
        float _BumpScale;
        float _DetailNormalScale;
        float _DetailTiling;

        float4 _SSSColor;
        float _SSSPower;
        float _SSSDistortion;
        float _SSSScale;
        float _SSSAmbient;

        float _Smoothness;
        float4 _SpecColor;
        float _FresnelPower;

        float _OcclusionStrength;
        float _ThicknessScale;

        struct Input
        {
            float2 uv_MainTex;
            float2 uv_BumpMap;
            float3 viewDir;
            float3 worldNormal;
            INTERNAL_DATA
        };

        struct SurfaceOutputSkinSSS
        {
            fixed3 Albedo;
            fixed3 Normal;
            fixed3 Emission;
            half Specular;
            fixed Gloss;
            fixed Alpha;
            fixed3 SSSColor;
            fixed Thickness;
            fixed Occlusion;
        };

        // Custom lighting function for SSS
        inline fixed4 LightingSkinSSS(SurfaceOutputSkinSSS s, fixed3 viewDir, UnityGI gi)
        {
            fixed3 lightDir = gi.light.dir;
            fixed3 lightColor = gi.light.color;

            // Standard diffuse
            fixed NdotL = max(0, dot(s.Normal, lightDir));
            fixed3 diffuse = s.Albedo * lightColor * NdotL;

            // Subsurface scattering
            fixed3 sssLightDir = lightDir + s.Normal * _SSSDistortion;
            fixed sssDot = pow(saturate(dot(viewDir, -sssLightDir)), _SSSPower) * _SSSScale;
            fixed3 sss = s.SSSColor * lightColor * sssDot * s.Thickness;
            sss += s.SSSColor * _SSSAmbient * s.Thickness;

            // Specular (Blinn-Phong)
            fixed3 halfDir = normalize(lightDir + viewDir);
            fixed NdotH = max(0, dot(s.Normal, halfDir));
            fixed spec = pow(NdotH, s.Gloss * 128) * s.Specular;
            fixed3 specular = _SpecColor.rgb * lightColor * spec;

            // Fresnel rim
            fixed fresnel = pow(1 - saturate(dot(s.Normal, viewDir)), _FresnelPower);
            fixed3 rim = _SpecColor.rgb * fresnel * 0.3;

            // Combine
            fixed3 color = diffuse + sss + specular + rim;
            color *= s.Occlusion;

            // Add ambient
            color += s.Albedo * gi.indirect.diffuse * s.Occlusion;
            color += gi.indirect.specular * fresnel * s.Specular;

            return fixed4(color, s.Alpha);
        }

        inline void LightingSkinSSS_GI(SurfaceOutputSkinSSS s, UnityGIInput data, inout UnityGI gi)
        {
            gi = UnityGlobalIllumination(data, 1.0, s.Normal);
        }

        void surf(Input IN, inout SurfaceOutputSkinSSS o)
        {
            // Albedo
            fixed4 c = tex2D(_MainTex, IN.uv_MainTex) * _Color;
            o.Albedo = c.rgb;
            o.Alpha = c.a;

            // Normal mapping with detail
            fixed3 mainNormal = UnpackScaleNormal(tex2D(_BumpMap, IN.uv_BumpMap), _BumpScale);
            fixed3 detailNormal = UnpackScaleNormal(tex2D(_DetailNormalMap, IN.uv_MainTex * _DetailTiling), _DetailNormalScale);
            o.Normal = normalize(mainNormal + detailNormal);

            // Specular
            o.Specular = _SpecColor.a;
            o.Gloss = _Smoothness;

            // SSS
            o.SSSColor = _SSSColor.rgb;
            o.Thickness = tex2D(_ThicknessMap, IN.uv_MainTex).r * _ThicknessScale;

            // Occlusion
            o.Occlusion = lerp(1, tex2D(_OcclusionMap, IN.uv_MainTex).r, _OcclusionStrength);
        }
        ENDCG
    }

    FallBack "Standard"
}
