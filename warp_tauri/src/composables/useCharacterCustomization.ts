/**
 * useCharacterCustomization - Sims 4-Style Character Creator
 *
 * Complete body customization system with:
 * - Visual slider controls (like Sims 4)
 * - Natural language parsing ("make him taller with bigger arms")
 * - Real-time preview via avatar bridge
 * - Preset system (athletic, dad bod, twink, bear, etc.)
 * - Import/export character configurations
 *
 * All parameters map to blend shapes in the 3D model.
 */

import { ref, reactive, computed, watch } from 'vue'
import { useAvatarBridge } from './useAvatarBridge'
import { useAI } from './useAI'

// ============================================================================
// TYPES
// ============================================================================

export interface BodyParameters {
  // Overall
  height: number              // 0-1 (5'4" to 6'6")
  weight: number              // 0-1 (lean to heavy)
  muscularity: number         // 0-1 (toned to bodybuilder)
  bodyFat: number             // 0-1 (cut to soft)
  age: number                 // 0-1 (20s to 50s appearance)

  // Upper Body
  shoulderWidth: number       // 0-1
  chestSize: number           // 0-1 (pec size)
  chestDefinition: number     // 0-1 (pec separation/definition)
  nippleSize: number          // 0-1
  nipplePosition: number      // 0-1 (higher to lower)
  armSize: number             // 0-1 (bicep/tricep)
  forearmSize: number         // 0-1
  handSize: number            // 0-1
  neckThickness: number       // 0-1
  trapsSize: number           // 0-1

  // Core
  waistWidth: number          // 0-1
  absDefinition: number       // 0-1 (smooth to 8-pack)
  vTaperIntensity: number     // 0-1 (shoulder to waist ratio)
  loveHandles: number         // 0-1
  backWidth: number           // 0-1 (lats)

  // Lower Body
  hipWidth: number            // 0-1
  buttSize: number            // 0-1
  buttShape: number           // 0-1 (flat to round/bubble)
  buttFirmness: number        // 0-1 (soft to firm)
  thighSize: number           // 0-1
  thighGap: number            // 0-1
  calfSize: number            // 0-1
  calfDefinition: number      // 0-1
  ankleThickness: number      // 0-1
  footSize: number            // 0-1

  // Anatomy (Genitals)
  penisLength: number         // 0-1 (4" to 10" flaccid visual)
  penisGirth: number          // 0-1
  penisHeadSize: number       // 0-1 (glans proportion)
  penisCurvature: number      // -1 to 1 (left curve, straight, right curve)
  penisCurvatureUp: number    // -1 to 1 (down curve, straight, up curve)
  penisVeininess: number      // 0-1
  circumcised: number         // 0-1 (0=uncut, 1=cut)
  foreskinLength: number      // 0-1 (if uncircumcised)
  scrotumSize: number         // 0-1 (ball sack size)
  testicleSize: number        // 0-1 (actual balls)
  testicleHang: number        // 0-1 (tight to hanging)
  testicleAsymmetry: number   // 0-1 (one lower than other)
  pubicHairDensity: number    // 0-1
  pubicHairStyle: number      // 0-1 (natural, trimmed, shaved gradient)
  groinDefinition: number     // 0-1 (V-lines/adonis belt)

  // Skin & Hair
  skinTone: number            // 0-1 (light to dark)
  skinTexture: number         // 0-1 (smooth to textured)
  bodyHairDensity: number     // 0-1
  bodyHairPattern: number     // 0-1 (sparse to full coverage)
  tanLines: number            // 0-1 (none to prominent)
  freckles: number            // 0-1
  scars: number               // 0-1 (none to some)
  veinyness: number           // 0-1 (overall body vein visibility)

  // Posture & Stance
  postureConfidence: number   // 0-1 (slouched to proud chest out)
  shoulderRoll: number        // -1 to 1 (forward to back)
  hipTilt: number             // -1 to 1 (anterior to posterior)
  headTilt: number            // -1 to 1 (down to up)
  stanceWidth: number         // 0-1 (narrow to wide)
}

export interface FaceParameters {
  // Face Shape
  faceLength: number          // 0-1
  faceWidth: number           // 0-1
  jawWidth: number            // 0-1
  jawDefinition: number       // 0-1 (soft to chiseled)
  chinSize: number            // 0-1
  chinShape: number           // 0-1 (rounded to square)
  chinCleft: number           // 0-1
  cheekboneHeight: number     // 0-1
  cheekboneProminence: number // 0-1
  cheekFullness: number       // 0-1

  // Forehead
  foreheadHeight: number      // 0-1
  foreheadWidth: number       // 0-1
  foreheadSlope: number       // 0-1
  browRidgeSize: number       // 0-1

  // Eyes
  eyeSize: number             // 0-1
  eyeWidth: number            // 0-1
  eyeSpacing: number          // 0-1
  eyeDepth: number            // 0-1 (protruding to deep-set)
  eyeTilt: number             // -1 to 1 (down to up outer corner)
  eyeColor: number            // 0-1 (maps to color palette)
  eyebrowThickness: number    // 0-1
  eyebrowArch: number         // 0-1
  eyebrowSpacing: number      // 0-1
  eyelashLength: number       // 0-1
  upperEyelid: number         // 0-1 (hooded to open)
  lowerEyelid: number         // 0-1 (bags)
  crowsFeet: number           // 0-1

  // Nose
  noseLength: number          // 0-1
  noseWidth: number           // 0-1
  noseBridgeHeight: number    // 0-1
  noseBridgeWidth: number     // 0-1
  noseTipSize: number         // 0-1
  noseTipShape: number        // 0-1 (upturned to downturned)
  nostrilSize: number         // 0-1
  nostrilFlare: number        // 0-1

  // Mouth & Lips
  mouthWidth: number          // 0-1
  mouthPosition: number       // 0-1 (vertical)
  upperLipSize: number        // 0-1
  lowerLipSize: number        // 0-1
  lipFullness: number         // 0-1
  lipColor: number            // 0-1
  cupidsBow: number           // 0-1
  mouthCorners: number        // -1 to 1 (down to up, resting expression)
  philtrumDepth: number       // 0-1

  // Ears
  earSize: number             // 0-1
  earAngle: number            // 0-1 (flat to protruding)
  earlobeSize: number         // 0-1
  earlobeAttached: number     // 0-1 (attached to free)

  // Facial Hair
  beardDensity: number        // 0-1
  beardLength: number         // 0-1
  beardStyle: number          // 0-1 (clean to full beard gradient)
  mustacheSize: number        // 0-1
  sideburnsLength: number     // 0-1
  stubbleAmount: number       // 0-1
  beardGray: number           // 0-1

  // Hair
  hairStyle: number           // 0-1 (maps to style presets)
  hairLength: number          // 0-1
  hairVolume: number          // 0-1
  hairColor: number           // 0-1 (maps to color palette)
  hairGray: number            // 0-1
  hairlineRecession: number   // 0-1
  hairPartSide: number        // 0-1 (left, center, right)
  hairTexture: number         // 0-1 (straight to curly)

  // Age & Character
  wrinkleForehead: number     // 0-1
  wrinkleEyes: number         // 0-1
  wrinkleMouth: number        // 0-1
  skinAge: number             // 0-1
  facialAsymmetry: number     // 0-1 (natural imperfection)
}

export interface CharacterConfig {
  name: string
  body: BodyParameters
  face: FaceParameters
  createdAt: number
  updatedAt: number
  presetBase?: string
}

export interface CharacterPreset {
  id: string
  name: string
  description: string
  thumbnail?: string
  body: Partial<BodyParameters>
  face: Partial<FaceParameters>
}

// ============================================================================
// DEFAULT VALUES
// ============================================================================

const DEFAULT_BODY: BodyParameters = {
  // Overall
  height: 0.5,
  weight: 0.4,
  muscularity: 0.5,
  bodyFat: 0.3,
  age: 0.3,

  // Upper Body
  shoulderWidth: 0.5,
  chestSize: 0.5,
  chestDefinition: 0.5,
  nippleSize: 0.5,
  nipplePosition: 0.5,
  armSize: 0.5,
  forearmSize: 0.5,
  handSize: 0.5,
  neckThickness: 0.5,
  trapsSize: 0.4,

  // Core
  waistWidth: 0.4,
  absDefinition: 0.5,
  vTaperIntensity: 0.5,
  loveHandles: 0.2,
  backWidth: 0.5,

  // Lower Body
  hipWidth: 0.4,
  buttSize: 0.5,
  buttShape: 0.5,
  buttFirmness: 0.6,
  thighSize: 0.5,
  thighGap: 0.3,
  calfSize: 0.5,
  calfDefinition: 0.5,
  ankleThickness: 0.4,
  footSize: 0.5,

  // Anatomy
  penisLength: 0.5,
  penisGirth: 0.5,
  penisHeadSize: 0.5,
  penisCurvature: 0,
  penisCurvatureUp: 0.1,
  penisVeininess: 0.3,
  circumcised: 0,
  foreskinLength: 0.5,
  scrotumSize: 0.5,
  testicleSize: 0.5,
  testicleHang: 0.5,
  testicleAsymmetry: 0.3,
  pubicHairDensity: 0.5,
  pubicHairStyle: 0.5,
  groinDefinition: 0.5,

  // Skin
  skinTone: 0.3,
  skinTexture: 0.3,
  bodyHairDensity: 0.4,
  bodyHairPattern: 0.5,
  tanLines: 0,
  freckles: 0.1,
  scars: 0,
  veinyness: 0.3,

  // Posture
  postureConfidence: 0.7,
  shoulderRoll: 0,
  hipTilt: 0,
  headTilt: 0.1,
  stanceWidth: 0.5
}

const DEFAULT_FACE: FaceParameters = {
  // Face Shape
  faceLength: 0.5,
  faceWidth: 0.5,
  jawWidth: 0.6,
  jawDefinition: 0.6,
  chinSize: 0.5,
  chinShape: 0.6,
  chinCleft: 0.2,
  cheekboneHeight: 0.5,
  cheekboneProminence: 0.5,
  cheekFullness: 0.4,

  // Forehead
  foreheadHeight: 0.5,
  foreheadWidth: 0.5,
  foreheadSlope: 0.5,
  browRidgeSize: 0.5,

  // Eyes
  eyeSize: 0.5,
  eyeWidth: 0.5,
  eyeSpacing: 0.5,
  eyeDepth: 0.5,
  eyeTilt: 0.1,
  eyeColor: 0.3,
  eyebrowThickness: 0.5,
  eyebrowArch: 0.4,
  eyebrowSpacing: 0.5,
  eyelashLength: 0.3,
  upperEyelid: 0.5,
  lowerEyelid: 0.2,
  crowsFeet: 0.1,

  // Nose
  noseLength: 0.5,
  noseWidth: 0.5,
  noseBridgeHeight: 0.5,
  noseBridgeWidth: 0.4,
  noseTipSize: 0.5,
  noseTipShape: 0.5,
  nostrilSize: 0.5,
  nostrilFlare: 0.4,

  // Mouth
  mouthWidth: 0.5,
  mouthPosition: 0.5,
  upperLipSize: 0.5,
  lowerLipSize: 0.5,
  lipFullness: 0.5,
  lipColor: 0.5,
  cupidsBow: 0.5,
  mouthCorners: 0.1,
  philtrumDepth: 0.5,

  // Ears
  earSize: 0.5,
  earAngle: 0.3,
  earlobeSize: 0.5,
  earlobeAttached: 0.5,

  // Facial Hair
  beardDensity: 0.3,
  beardLength: 0.2,
  beardStyle: 0.3,
  mustacheSize: 0.3,
  sideburnsLength: 0.3,
  stubbleAmount: 0.4,
  beardGray: 0,

  // Hair
  hairStyle: 0.5,
  hairLength: 0.4,
  hairVolume: 0.5,
  hairColor: 0.3,
  hairGray: 0,
  hairlineRecession: 0.1,
  hairPartSide: 0.3,
  hairTexture: 0.3,

  // Age
  wrinkleForehead: 0.1,
  wrinkleEyes: 0.1,
  wrinkleMouth: 0.1,
  skinAge: 0.2,
  facialAsymmetry: 0.15
}

// ============================================================================
// PRESETS
// ============================================================================

const PRESETS: CharacterPreset[] = [
  {
    id: 'athletic',
    name: 'Athletic',
    description: 'Fit, toned swimmer/runner build',
    body: {
      muscularity: 0.6,
      bodyFat: 0.2,
      chestSize: 0.55,
      absDefinition: 0.7,
      vTaperIntensity: 0.6,
      buttFirmness: 0.7,
      postureConfidence: 0.75
    },
    face: {
      jawDefinition: 0.65
    }
  },
  {
    id: 'muscular',
    name: 'Muscular',
    description: 'Gym enthusiast, well-built',
    body: {
      muscularity: 0.8,
      bodyFat: 0.25,
      shoulderWidth: 0.7,
      chestSize: 0.75,
      chestDefinition: 0.7,
      armSize: 0.75,
      trapsSize: 0.6,
      backWidth: 0.7,
      thighSize: 0.65,
      calfSize: 0.6,
      veinyness: 0.5,
      postureConfidence: 0.8
    },
    face: {
      jawWidth: 0.65,
      neckThickness: 0.6
    }
  },
  {
    id: 'bodybuilder',
    name: 'Bodybuilder',
    description: 'Competition-ready physique',
    body: {
      muscularity: 1.0,
      bodyFat: 0.1,
      shoulderWidth: 0.85,
      chestSize: 0.9,
      chestDefinition: 0.9,
      armSize: 0.9,
      forearmSize: 0.75,
      trapsSize: 0.8,
      absDefinition: 0.95,
      vTaperIntensity: 0.85,
      backWidth: 0.9,
      thighSize: 0.85,
      calfSize: 0.75,
      veinyness: 0.8,
      groinDefinition: 0.8,
      postureConfidence: 0.9
    },
    face: {
      jawDefinition: 0.8
    }
  },
  {
    id: 'dadbod',
    name: 'Dad Bod',
    description: 'Comfortable, relaxed build',
    body: {
      muscularity: 0.35,
      bodyFat: 0.6,
      weight: 0.6,
      chestSize: 0.5,
      absDefinition: 0.15,
      waistWidth: 0.6,
      loveHandles: 0.5,
      buttSize: 0.55,
      buttFirmness: 0.4,
      postureConfidence: 0.5
    },
    face: {
      cheekFullness: 0.6,
      jawDefinition: 0.35
    }
  },
  {
    id: 'twink',
    name: 'Twink',
    description: 'Slim, youthful, smooth',
    body: {
      height: 0.35,
      weight: 0.25,
      muscularity: 0.25,
      bodyFat: 0.15,
      shoulderWidth: 0.35,
      chestSize: 0.3,
      armSize: 0.3,
      waistWidth: 0.3,
      hipWidth: 0.35,
      buttSize: 0.45,
      buttShape: 0.6,
      thighSize: 0.35,
      bodyHairDensity: 0.1,
      pubicHairDensity: 0.2,
      age: 0.15
    },
    face: {
      faceLength: 0.45,
      jawWidth: 0.4,
      jawDefinition: 0.4,
      cheekFullness: 0.45,
      beardDensity: 0,
      stubbleAmount: 0,
      skinAge: 0.1
    }
  },
  {
    id: 'bear',
    name: 'Bear',
    description: 'Large, hairy, powerful',
    body: {
      height: 0.7,
      weight: 0.75,
      muscularity: 0.5,
      bodyFat: 0.65,
      shoulderWidth: 0.7,
      chestSize: 0.7,
      neckThickness: 0.7,
      armSize: 0.65,
      waistWidth: 0.65,
      backWidth: 0.7,
      thighSize: 0.7,
      bodyHairDensity: 0.9,
      bodyHairPattern: 0.85,
      pubicHairDensity: 0.8
    },
    face: {
      faceWidth: 0.6,
      jawWidth: 0.65,
      beardDensity: 0.85,
      beardLength: 0.6
    }
  },
  {
    id: 'otter',
    name: 'Otter',
    description: 'Slim but hairy',
    body: {
      weight: 0.35,
      muscularity: 0.45,
      bodyFat: 0.25,
      bodyHairDensity: 0.75,
      bodyHairPattern: 0.7,
      chestSize: 0.45,
      absDefinition: 0.5
    },
    face: {
      beardDensity: 0.6,
      stubbleAmount: 0.7
    }
  },
  {
    id: 'jock',
    name: 'Jock',
    description: 'College athlete build',
    body: {
      height: 0.6,
      muscularity: 0.65,
      bodyFat: 0.2,
      shoulderWidth: 0.65,
      chestSize: 0.6,
      armSize: 0.6,
      absDefinition: 0.6,
      buttSize: 0.55,
      buttFirmness: 0.7,
      thighSize: 0.6,
      age: 0.2,
      postureConfidence: 0.75
    },
    face: {
      jawDefinition: 0.6,
      skinAge: 0.15
    }
  },
  {
    id: 'silver_fox',
    name: 'Silver Fox',
    description: 'Distinguished, mature, handsome',
    body: {
      height: 0.55,
      muscularity: 0.5,
      bodyFat: 0.35,
      age: 0.7,
      bodyHairDensity: 0.5,
      postureConfidence: 0.7
    },
    face: {
      hairGray: 0.8,
      beardGray: 0.7,
      beardDensity: 0.5,
      wrinkleForehead: 0.5,
      wrinkleEyes: 0.5,
      crowsFeet: 0.5,
      skinAge: 0.6,
      jawDefinition: 0.55
    }
  },
  {
    id: 'hung',
    name: 'Well Endowed',
    description: 'Emphasis on anatomy',
    body: {
      penisLength: 0.85,
      penisGirth: 0.75,
      penisHeadSize: 0.65,
      penisVeininess: 0.5,
      testicleSize: 0.7,
      scrotumSize: 0.7,
      testicleHang: 0.65,
      groinDefinition: 0.6
    },
    face: {}
  }
]

// ============================================================================
// NATURAL LANGUAGE MAPPINGS
// ============================================================================

interface NLPMapping {
  keywords: string[]
  parameter: keyof BodyParameters | keyof FaceParameters
  target: 'body' | 'face'
  direction: 'increase' | 'decrease' | 'set'
  value?: number
}

const NLP_MAPPINGS: NLPMapping[] = [
  // Height
  { keywords: ['taller', 'tall', 'height up', 'more height'], parameter: 'height', target: 'body', direction: 'increase' },
  { keywords: ['shorter', 'short', 'less height', 'height down'], parameter: 'height', target: 'body', direction: 'decrease' },

  // Build
  { keywords: ['bigger', 'larger', 'bulkier', 'more muscular', 'buffer', 'more muscle'], parameter: 'muscularity', target: 'body', direction: 'increase' },
  { keywords: ['smaller', 'slimmer', 'leaner', 'less muscular', 'less muscle'], parameter: 'muscularity', target: 'body', direction: 'decrease' },
  { keywords: ['fatter', 'heavier', 'thicker', 'more weight'], parameter: 'bodyFat', target: 'body', direction: 'increase' },
  { keywords: ['thinner', 'lighter', 'skinnier', 'less fat', 'cut', 'ripped', 'shredded'], parameter: 'bodyFat', target: 'body', direction: 'decrease' },

  // Upper body
  { keywords: ['broader shoulders', 'wider shoulders', 'bigger shoulders'], parameter: 'shoulderWidth', target: 'body', direction: 'increase' },
  { keywords: ['narrower shoulders', 'smaller shoulders'], parameter: 'shoulderWidth', target: 'body', direction: 'decrease' },
  { keywords: ['bigger chest', 'bigger pecs', 'more pecs', 'larger chest'], parameter: 'chestSize', target: 'body', direction: 'increase' },
  { keywords: ['smaller chest', 'smaller pecs', 'less chest'], parameter: 'chestSize', target: 'body', direction: 'decrease' },
  { keywords: ['bigger arms', 'larger arms', 'more arms', 'bigger biceps'], parameter: 'armSize', target: 'body', direction: 'increase' },
  { keywords: ['smaller arms', 'thinner arms', 'less arms'], parameter: 'armSize', target: 'body', direction: 'decrease' },

  // Core
  { keywords: ['more abs', 'defined abs', 'six pack', 'eight pack', 'ab definition'], parameter: 'absDefinition', target: 'body', direction: 'increase' },
  { keywords: ['less abs', 'smooth stomach', 'soft stomach'], parameter: 'absDefinition', target: 'body', direction: 'decrease' },
  { keywords: ['smaller waist', 'thinner waist', 'narrow waist'], parameter: 'waistWidth', target: 'body', direction: 'decrease' },
  { keywords: ['bigger waist', 'wider waist', 'thick waist'], parameter: 'waistWidth', target: 'body', direction: 'increase' },

  // Lower body
  { keywords: ['bigger butt', 'larger butt', 'more butt', 'bigger ass', 'more ass', 'thicc', 'bubble butt'], parameter: 'buttSize', target: 'body', direction: 'increase' },
  { keywords: ['smaller butt', 'less butt', 'flat butt', 'smaller ass'], parameter: 'buttSize', target: 'body', direction: 'decrease' },
  { keywords: ['rounder butt', 'bubble butt', 'peach'], parameter: 'buttShape', target: 'body', direction: 'increase' },
  { keywords: ['flatter butt', 'flat ass'], parameter: 'buttShape', target: 'body', direction: 'decrease' },
  { keywords: ['bigger thighs', 'thicker thighs', 'more thighs'], parameter: 'thighSize', target: 'body', direction: 'increase' },
  { keywords: ['smaller thighs', 'thinner thighs', 'skinny legs'], parameter: 'thighSize', target: 'body', direction: 'decrease' },
  { keywords: ['bigger calves', 'larger calves', 'more calves'], parameter: 'calfSize', target: 'body', direction: 'increase' },
  { keywords: ['smaller calves', 'thinner calves'], parameter: 'calfSize', target: 'body', direction: 'decrease' },

  // Anatomy
  { keywords: ['bigger dick', 'larger dick', 'bigger cock', 'larger cock', 'bigger penis', 'more length', 'longer dick', 'longer cock', 'hung'], parameter: 'penisLength', target: 'body', direction: 'increase' },
  { keywords: ['smaller dick', 'smaller cock', 'shorter dick', 'less length'], parameter: 'penisLength', target: 'body', direction: 'decrease' },
  { keywords: ['thicker dick', 'thicker cock', 'more girth', 'girthier'], parameter: 'penisGirth', target: 'body', direction: 'increase' },
  { keywords: ['thinner dick', 'thinner cock', 'less girth'], parameter: 'penisGirth', target: 'body', direction: 'decrease' },
  { keywords: ['bigger head', 'larger head', 'mushroom'], parameter: 'penisHeadSize', target: 'body', direction: 'increase' },
  { keywords: ['curved left'], parameter: 'penisCurvature', target: 'body', direction: 'decrease' },
  { keywords: ['curved right'], parameter: 'penisCurvature', target: 'body', direction: 'increase' },
  { keywords: ['curved up', 'upward curve', 'banana'], parameter: 'penisCurvatureUp', target: 'body', direction: 'increase' },
  { keywords: ['curved down', 'downward curve'], parameter: 'penisCurvatureUp', target: 'body', direction: 'decrease' },
  { keywords: ['straight dick', 'no curve'], parameter: 'penisCurvature', target: 'body', direction: 'set', value: 0 },
  { keywords: ['more veins', 'veinier', 'veiny dick'], parameter: 'penisVeininess', target: 'body', direction: 'increase' },
  { keywords: ['less veins', 'smooth dick'], parameter: 'penisVeininess', target: 'body', direction: 'decrease' },
  { keywords: ['circumcised', 'cut'], parameter: 'circumcised', target: 'body', direction: 'set', value: 1 },
  { keywords: ['uncircumcised', 'uncut', 'foreskin'], parameter: 'circumcised', target: 'body', direction: 'set', value: 0 },
  { keywords: ['bigger balls', 'larger balls', 'big balls'], parameter: 'testicleSize', target: 'body', direction: 'increase' },
  { keywords: ['smaller balls'], parameter: 'testicleSize', target: 'body', direction: 'decrease' },
  { keywords: ['hanging balls', 'low hangers', 'saggy balls'], parameter: 'testicleHang', target: 'body', direction: 'increase' },
  { keywords: ['tight balls', 'high balls'], parameter: 'testicleHang', target: 'body', direction: 'decrease' },

  // Hair
  { keywords: ['more body hair', 'hairier', 'hairy'], parameter: 'bodyHairDensity', target: 'body', direction: 'increase' },
  { keywords: ['less body hair', 'smooth', 'hairless', 'shaved'], parameter: 'bodyHairDensity', target: 'body', direction: 'decrease' },
  { keywords: ['more pubes', 'bushy', 'natural pubes'], parameter: 'pubicHairDensity', target: 'body', direction: 'increase' },
  { keywords: ['trimmed pubes', 'manscaped'], parameter: 'pubicHairDensity', target: 'body', direction: 'set', value: 0.4 },
  { keywords: ['shaved pubes', 'no pubes', 'bare'], parameter: 'pubicHairDensity', target: 'body', direction: 'set', value: 0 },

  // Skin
  { keywords: ['darker skin', 'tanned', 'more tan'], parameter: 'skinTone', target: 'body', direction: 'increase' },
  { keywords: ['lighter skin', 'paler', 'fair'], parameter: 'skinTone', target: 'body', direction: 'decrease' },
  { keywords: ['tan lines'], parameter: 'tanLines', target: 'body', direction: 'increase' },

  // Posture
  { keywords: ['confident posture', 'stand tall', 'proud', 'chest out'], parameter: 'postureConfidence', target: 'body', direction: 'increase' },
  { keywords: ['relaxed posture', 'casual', 'slouched'], parameter: 'postureConfidence', target: 'body', direction: 'decrease' },

  // Face - Jaw/Chin
  { keywords: ['stronger jaw', 'bigger jaw', 'wider jaw', 'masculine jaw'], parameter: 'jawWidth', target: 'face', direction: 'increase' },
  { keywords: ['softer jaw', 'narrower jaw', 'smaller jaw'], parameter: 'jawWidth', target: 'face', direction: 'decrease' },
  { keywords: ['chiseled jaw', 'defined jaw', 'sharp jaw'], parameter: 'jawDefinition', target: 'face', direction: 'increase' },
  { keywords: ['soft jaw', 'round jaw'], parameter: 'jawDefinition', target: 'face', direction: 'decrease' },
  { keywords: ['bigger chin', 'prominent chin'], parameter: 'chinSize', target: 'face', direction: 'increase' },
  { keywords: ['smaller chin', 'less chin'], parameter: 'chinSize', target: 'face', direction: 'decrease' },
  { keywords: ['cleft chin', 'chin dimple', 'butt chin'], parameter: 'chinCleft', target: 'face', direction: 'increase' },

  // Face - Cheeks
  { keywords: ['higher cheekbones', 'prominent cheekbones'], parameter: 'cheekboneProminence', target: 'face', direction: 'increase' },
  { keywords: ['fuller cheeks', 'chubby cheeks'], parameter: 'cheekFullness', target: 'face', direction: 'increase' },
  { keywords: ['hollow cheeks', 'gaunt'], parameter: 'cheekFullness', target: 'face', direction: 'decrease' },

  // Face - Eyes
  { keywords: ['bigger eyes', 'larger eyes'], parameter: 'eyeSize', target: 'face', direction: 'increase' },
  { keywords: ['smaller eyes', 'squinty'], parameter: 'eyeSize', target: 'face', direction: 'decrease' },
  { keywords: ['deeper eyes', 'deep set eyes'], parameter: 'eyeDepth', target: 'face', direction: 'increase' },
  { keywords: ['thicker eyebrows', 'bushy brows'], parameter: 'eyebrowThickness', target: 'face', direction: 'increase' },
  { keywords: ['thinner eyebrows', 'groomed brows'], parameter: 'eyebrowThickness', target: 'face', direction: 'decrease' },

  // Face - Nose
  { keywords: ['bigger nose', 'larger nose', 'prominent nose'], parameter: 'noseLength', target: 'face', direction: 'increase' },
  { keywords: ['smaller nose', 'button nose'], parameter: 'noseLength', target: 'face', direction: 'decrease' },
  { keywords: ['wider nose'], parameter: 'noseWidth', target: 'face', direction: 'increase' },
  { keywords: ['narrower nose', 'thin nose'], parameter: 'noseWidth', target: 'face', direction: 'decrease' },

  // Face - Lips
  { keywords: ['fuller lips', 'bigger lips', 'thick lips'], parameter: 'lipFullness', target: 'face', direction: 'increase' },
  { keywords: ['thinner lips', 'smaller lips'], parameter: 'lipFullness', target: 'face', direction: 'decrease' },

  // Face - Facial hair
  { keywords: ['more beard', 'fuller beard', 'thick beard'], parameter: 'beardDensity', target: 'face', direction: 'increase' },
  { keywords: ['less beard', 'trim beard', 'stubble'], parameter: 'beardDensity', target: 'face', direction: 'decrease' },
  { keywords: ['clean shaven', 'no beard', 'shaved face'], parameter: 'beardDensity', target: 'face', direction: 'set', value: 0 },
  { keywords: ['longer beard'], parameter: 'beardLength', target: 'face', direction: 'increase' },
  { keywords: ['shorter beard'], parameter: 'beardLength', target: 'face', direction: 'decrease' },
  { keywords: ['5 oclock shadow', 'scruff', 'scruffy'], parameter: 'stubbleAmount', target: 'face', direction: 'set', value: 0.6 },

  // Face - Hair
  { keywords: ['longer hair'], parameter: 'hairLength', target: 'face', direction: 'increase' },
  { keywords: ['shorter hair', 'buzz cut', 'short hair'], parameter: 'hairLength', target: 'face', direction: 'decrease' },
  { keywords: ['bald', 'shaved head', 'no hair'], parameter: 'hairLength', target: 'face', direction: 'set', value: 0 },
  { keywords: ['more volume', 'thicker hair', 'fuller hair'], parameter: 'hairVolume', target: 'face', direction: 'increase' },
  { keywords: ['curly hair', 'curls'], parameter: 'hairTexture', target: 'face', direction: 'increase' },
  { keywords: ['straight hair'], parameter: 'hairTexture', target: 'face', direction: 'decrease' },
  { keywords: ['gray hair', 'grey hair', 'silver hair', 'white hair'], parameter: 'hairGray', target: 'face', direction: 'increase' },
  { keywords: ['receding hairline', 'balding'], parameter: 'hairlineRecession', target: 'face', direction: 'increase' },

  // Age
  { keywords: ['older', 'more mature', 'aged'], parameter: 'skinAge', target: 'face', direction: 'increase' },
  { keywords: ['younger', 'more youthful', 'less aged'], parameter: 'skinAge', target: 'face', direction: 'decrease' },
  { keywords: ['more wrinkles'], parameter: 'wrinkleForehead', target: 'face', direction: 'increase' },
  { keywords: ['less wrinkles', 'smooth skin'], parameter: 'wrinkleForehead', target: 'face', direction: 'decrease' }
]

// ============================================================================
// STORAGE
// ============================================================================

const CONFIG_KEY = 'warp_character_config'
const SAVED_CHARACTERS_KEY = 'warp_saved_characters'

function loadConfig(): CharacterConfig | null {
  try {
    const stored = localStorage.getItem(CONFIG_KEY)
    if (stored) return JSON.parse(stored)
  } catch {}
  return null
}

function saveConfig(config: CharacterConfig): void {
  localStorage.setItem(CONFIG_KEY, JSON.stringify(config))
}

function loadSavedCharacters(): CharacterConfig[] {
  try {
    const stored = localStorage.getItem(SAVED_CHARACTERS_KEY)
    if (stored) return JSON.parse(stored)
  } catch {}
  return []
}

function saveSavedCharacters(characters: CharacterConfig[]): void {
  localStorage.setItem(SAVED_CHARACTERS_KEY, JSON.stringify(characters))
}

// ============================================================================
// COMPOSABLE
// ============================================================================

export function useCharacterCustomization() {
  const avatarBridge = useAvatarBridge()
  const ai = useAI()

  // Current character config
  const config = ref<CharacterConfig>(loadConfig() || {
    name: 'SAM',
    body: { ...DEFAULT_BODY },
    face: { ...DEFAULT_FACE },
    createdAt: Date.now(),
    updatedAt: Date.now()
  })

  // Saved characters
  const savedCharacters = ref<CharacterConfig[]>(loadSavedCharacters())

  // UI state
  const activeCategory = ref<string>('body')
  const activeSubCategory = ref<string>('overall')
  const previewMode = ref<'full' | 'face' | 'body' | 'anatomy'>('full')
  const showComparison = ref(false)
  const comparisonConfig = ref<CharacterConfig | null>(null)

  // ========================================================================
  // PARAMETER CATEGORIES (for UI organization)
  // ========================================================================

  const bodyCategories = {
    overall: ['height', 'weight', 'muscularity', 'bodyFat', 'age'],
    upperBody: ['shoulderWidth', 'chestSize', 'chestDefinition', 'nippleSize', 'nipplePosition', 'armSize', 'forearmSize', 'handSize', 'neckThickness', 'trapsSize'],
    core: ['waistWidth', 'absDefinition', 'vTaperIntensity', 'loveHandles', 'backWidth'],
    lowerBody: ['hipWidth', 'buttSize', 'buttShape', 'buttFirmness', 'thighSize', 'thighGap', 'calfSize', 'calfDefinition', 'ankleThickness', 'footSize'],
    anatomy: ['penisLength', 'penisGirth', 'penisHeadSize', 'penisCurvature', 'penisCurvatureUp', 'penisVeininess', 'circumcised', 'foreskinLength', 'scrotumSize', 'testicleSize', 'testicleHang', 'testicleAsymmetry', 'pubicHairDensity', 'pubicHairStyle', 'groinDefinition'],
    skin: ['skinTone', 'skinTexture', 'bodyHairDensity', 'bodyHairPattern', 'tanLines', 'freckles', 'scars', 'veinyness'],
    posture: ['postureConfidence', 'shoulderRoll', 'hipTilt', 'headTilt', 'stanceWidth']
  }

  const faceCategories = {
    faceShape: ['faceLength', 'faceWidth', 'jawWidth', 'jawDefinition', 'chinSize', 'chinShape', 'chinCleft', 'cheekboneHeight', 'cheekboneProminence', 'cheekFullness'],
    forehead: ['foreheadHeight', 'foreheadWidth', 'foreheadSlope', 'browRidgeSize'],
    eyes: ['eyeSize', 'eyeWidth', 'eyeSpacing', 'eyeDepth', 'eyeTilt', 'eyeColor', 'eyebrowThickness', 'eyebrowArch', 'eyebrowSpacing', 'eyelashLength', 'upperEyelid', 'lowerEyelid', 'crowsFeet'],
    nose: ['noseLength', 'noseWidth', 'noseBridgeHeight', 'noseBridgeWidth', 'noseTipSize', 'noseTipShape', 'nostrilSize', 'nostrilFlare'],
    mouth: ['mouthWidth', 'mouthPosition', 'upperLipSize', 'lowerLipSize', 'lipFullness', 'lipColor', 'cupidsBow', 'mouthCorners', 'philtrumDepth'],
    ears: ['earSize', 'earAngle', 'earlobeSize', 'earlobeAttached'],
    facialHair: ['beardDensity', 'beardLength', 'beardStyle', 'mustacheSize', 'sideburnsLength', 'stubbleAmount', 'beardGray'],
    hair: ['hairStyle', 'hairLength', 'hairVolume', 'hairColor', 'hairGray', 'hairlineRecession', 'hairPartSide', 'hairTexture'],
    age: ['wrinkleForehead', 'wrinkleEyes', 'wrinkleMouth', 'skinAge', 'facialAsymmetry']
  }

  // ========================================================================
  // PARAMETER DISPLAY NAMES
  // ========================================================================

  const parameterLabels: Record<string, string> = {
    // Body
    height: 'Height',
    weight: 'Weight',
    muscularity: 'Muscularity',
    bodyFat: 'Body Fat',
    age: 'Body Age',
    shoulderWidth: 'Shoulder Width',
    chestSize: 'Chest/Pec Size',
    chestDefinition: 'Chest Definition',
    nippleSize: 'Nipple Size',
    nipplePosition: 'Nipple Position',
    armSize: 'Arm Size',
    forearmSize: 'Forearm Size',
    handSize: 'Hand Size',
    neckThickness: 'Neck Thickness',
    trapsSize: 'Traps Size',
    waistWidth: 'Waist Width',
    absDefinition: 'Abs Definition',
    vTaperIntensity: 'V-Taper',
    loveHandles: 'Love Handles',
    backWidth: 'Back Width',
    hipWidth: 'Hip Width',
    buttSize: 'Butt Size',
    buttShape: 'Butt Shape',
    buttFirmness: 'Butt Firmness',
    thighSize: 'Thigh Size',
    thighGap: 'Thigh Gap',
    calfSize: 'Calf Size',
    calfDefinition: 'Calf Definition',
    ankleThickness: 'Ankle Thickness',
    footSize: 'Foot Size',
    penisLength: 'Length',
    penisGirth: 'Girth',
    penisHeadSize: 'Head Size',
    penisCurvature: 'Curve (L/R)',
    penisCurvatureUp: 'Curve (Up/Down)',
    penisVeininess: 'Veininess',
    circumcised: 'Circumcised',
    foreskinLength: 'Foreskin',
    scrotumSize: 'Scrotum Size',
    testicleSize: 'Testicle Size',
    testicleHang: 'Hang',
    testicleAsymmetry: 'Asymmetry',
    pubicHairDensity: 'Pubic Hair',
    pubicHairStyle: 'Pubic Style',
    groinDefinition: 'V-Lines',
    skinTone: 'Skin Tone',
    skinTexture: 'Skin Texture',
    bodyHairDensity: 'Body Hair',
    bodyHairPattern: 'Hair Pattern',
    tanLines: 'Tan Lines',
    freckles: 'Freckles',
    scars: 'Scars',
    veinyness: 'Vein Visibility',
    postureConfidence: 'Confidence',
    shoulderRoll: 'Shoulder Roll',
    hipTilt: 'Hip Tilt',
    headTilt: 'Head Tilt',
    stanceWidth: 'Stance Width',

    // Face
    faceLength: 'Face Length',
    faceWidth: 'Face Width',
    jawWidth: 'Jaw Width',
    jawDefinition: 'Jaw Definition',
    chinSize: 'Chin Size',
    chinShape: 'Chin Shape',
    chinCleft: 'Chin Cleft',
    cheekboneHeight: 'Cheekbone Height',
    cheekboneProminence: 'Cheekbone Prominence',
    cheekFullness: 'Cheek Fullness',
    foreheadHeight: 'Forehead Height',
    foreheadWidth: 'Forehead Width',
    foreheadSlope: 'Forehead Slope',
    browRidgeSize: 'Brow Ridge',
    eyeSize: 'Eye Size',
    eyeWidth: 'Eye Width',
    eyeSpacing: 'Eye Spacing',
    eyeDepth: 'Eye Depth',
    eyeTilt: 'Eye Tilt',
    eyeColor: 'Eye Color',
    eyebrowThickness: 'Eyebrow Thickness',
    eyebrowArch: 'Eyebrow Arch',
    eyebrowSpacing: 'Eyebrow Spacing',
    eyelashLength: 'Eyelash Length',
    upperEyelid: 'Upper Eyelid',
    lowerEyelid: 'Under-Eye',
    crowsFeet: "Crow's Feet",
    noseLength: 'Nose Length',
    noseWidth: 'Nose Width',
    noseBridgeHeight: 'Bridge Height',
    noseBridgeWidth: 'Bridge Width',
    noseTipSize: 'Tip Size',
    noseTipShape: 'Tip Shape',
    nostrilSize: 'Nostril Size',
    nostrilFlare: 'Nostril Flare',
    mouthWidth: 'Mouth Width',
    mouthPosition: 'Mouth Position',
    upperLipSize: 'Upper Lip',
    lowerLipSize: 'Lower Lip',
    lipFullness: 'Lip Fullness',
    lipColor: 'Lip Color',
    cupidsBow: "Cupid's Bow",
    mouthCorners: 'Mouth Corners',
    philtrumDepth: 'Philtrum Depth',
    earSize: 'Ear Size',
    earAngle: 'Ear Angle',
    earlobeSize: 'Earlobe Size',
    earlobeAttached: 'Earlobe Type',
    beardDensity: 'Beard Density',
    beardLength: 'Beard Length',
    beardStyle: 'Beard Style',
    mustacheSize: 'Mustache',
    sideburnsLength: 'Sideburns',
    stubbleAmount: 'Stubble',
    beardGray: 'Beard Gray',
    hairStyle: 'Hair Style',
    hairLength: 'Hair Length',
    hairVolume: 'Hair Volume',
    hairColor: 'Hair Color',
    hairGray: 'Gray Hair',
    hairlineRecession: 'Hairline',
    hairPartSide: 'Part Side',
    hairTexture: 'Hair Texture',
    wrinkleForehead: 'Forehead Lines',
    wrinkleEyes: 'Eye Wrinkles',
    wrinkleMouth: 'Mouth Lines',
    skinAge: 'Skin Age',
    facialAsymmetry: 'Asymmetry'
  }

  // ========================================================================
  // COMPUTED
  // ========================================================================

  const currentPreset = computed(() => {
    // Try to match current config to a preset
    for (const preset of PRESETS) {
      let matches = 0
      let total = 0

      for (const [key, value] of Object.entries(preset.body)) {
        total++
        if (Math.abs((config.value.body as any)[key] - (value as number)) < 0.1) {
          matches++
        }
      }

      for (const [key, value] of Object.entries(preset.face)) {
        total++
        if (Math.abs((config.value.face as any)[key] - (value as number)) < 0.1) {
          matches++
        }
      }

      if (total > 0 && matches / total > 0.8) {
        return preset.id
      }
    }
    return null
  })

  const heightDisplay = computed(() => {
    // Map 0-1 to 5'4" to 6'6"
    const inches = 64 + config.value.body.height * 14
    const feet = Math.floor(inches / 12)
    const remainingInches = Math.round(inches % 12)
    const cm = Math.round(inches * 2.54)
    return `${feet}'${remainingInches}" (${cm}cm)`
  })

  // ========================================================================
  // METHODS
  // ========================================================================

  /**
   * Set a body parameter
   */
  function setBodyParam(param: keyof BodyParameters, value: number): void {
    config.value.body[param] = Math.max(-1, Math.min(1, value))
    config.value.updatedAt = Date.now()
    syncToAvatar()
    saveConfig(config.value)
  }

  /**
   * Set a face parameter
   */
  function setFaceParam(param: keyof FaceParameters, value: number): void {
    config.value.face[param] = Math.max(-1, Math.min(1, value))
    config.value.updatedAt = Date.now()
    syncToAvatar()
    saveConfig(config.value)
  }

  /**
   * Apply a preset
   */
  function applyPreset(presetId: string): void {
    const preset = PRESETS.find(p => p.id === presetId)
    if (!preset) return

    // Apply preset values on top of current config
    for (const [key, value] of Object.entries(preset.body)) {
      (config.value.body as any)[key] = value
    }

    for (const [key, value] of Object.entries(preset.face)) {
      (config.value.face as any)[key] = value
    }

    config.value.presetBase = presetId
    config.value.updatedAt = Date.now()
    syncToAvatar()
    saveConfig(config.value)
  }

  /**
   * Reset to defaults
   */
  function resetToDefaults(): void {
    config.value.body = { ...DEFAULT_BODY }
    config.value.face = { ...DEFAULT_FACE }
    config.value.presetBase = undefined
    config.value.updatedAt = Date.now()
    syncToAvatar()
    saveConfig(config.value)
  }

  /**
   * Randomize within constraints
   */
  function randomize(category?: string): void {
    const randomInRange = (min: number, max: number) =>
      min + Math.random() * (max - min)

    if (!category || category === 'body') {
      for (const key of Object.keys(config.value.body)) {
        (config.value.body as any)[key] = randomInRange(0.2, 0.8)
      }
    }

    if (!category || category === 'face') {
      for (const key of Object.keys(config.value.face)) {
        (config.value.face as any)[key] = randomInRange(0.2, 0.8)
      }
    }

    config.value.updatedAt = Date.now()
    syncToAvatar()
    saveConfig(config.value)
  }

  /**
   * Parse natural language description and apply changes
   */
  async function applyDescription(description: string): Promise<{
    applied: string[]
    notUnderstood: string[]
  }> {
    const applied: string[] = []
    const notUnderstood: string[] = []
    const lowerDesc = description.toLowerCase()

    // Check each NLP mapping
    for (const mapping of NLP_MAPPINGS) {
      for (const keyword of mapping.keywords) {
        if (lowerDesc.includes(keyword)) {
          const currentValue = mapping.target === 'body'
            ? (config.value.body as any)[mapping.parameter]
            : (config.value.face as any)[mapping.parameter]

          let newValue: number

          if (mapping.direction === 'set' && mapping.value !== undefined) {
            newValue = mapping.value
          } else if (mapping.direction === 'increase') {
            newValue = Math.min(1, currentValue + 0.15)
          } else {
            newValue = Math.max(0, currentValue - 0.15)
          }

          if (mapping.target === 'body') {
            setBodyParam(mapping.parameter as keyof BodyParameters, newValue)
          } else {
            setFaceParam(mapping.parameter as keyof FaceParameters, newValue)
          }

          applied.push(`${parameterLabels[mapping.parameter]}: ${mapping.direction}`)
          break
        }
      }
    }

    // Check for preset keywords
    for (const preset of PRESETS) {
      if (lowerDesc.includes(preset.id) || lowerDesc.includes(preset.name.toLowerCase())) {
        applyPreset(preset.id)
        applied.push(`Applied preset: ${preset.name}`)
        break
      }
    }

    // If nothing was understood, try AI parsing
    if (applied.length === 0) {
      try {
        const aiResult = await parseWithAI(description)
        if (aiResult) {
          for (const [param, value] of Object.entries(aiResult.body || {})) {
            setBodyParam(param as keyof BodyParameters, value as number)
            applied.push(`${parameterLabels[param]}: ${value}`)
          }
          for (const [param, value] of Object.entries(aiResult.face || {})) {
            setFaceParam(param as keyof FaceParameters, value as number)
            applied.push(`${parameterLabels[param]}: ${value}`)
          }
        }
      } catch {
        notUnderstood.push(description)
      }
    }

    return { applied, notUnderstood }
  }

  /**
   * Use AI to parse complex descriptions
   */
  async function parseWithAI(description: string): Promise<{
    body?: Partial<BodyParameters>
    face?: Partial<FaceParameters>
  } | null> {
    const prompt = `Parse this character description into parameter values (0-1 scale).
Description: "${description}"

Available parameters:
Body: height, muscularity, bodyFat, chestSize, armSize, buttSize, penisLength, penisGirth, testicleSize
Face: jawWidth, jawDefinition, beardDensity, hairLength, eyeSize

Return ONLY a JSON object with body and/or face keys containing parameter:value pairs.
Example: {"body": {"muscularity": 0.8, "height": 0.7}, "face": {"beardDensity": 0.5}}`

    const response = await ai.chat([
      { role: 'user', content: prompt }
    ])

    try {
      // Extract JSON from response
      const jsonMatch = response.match(/\{[\s\S]*\}/)
      if (jsonMatch) {
        return JSON.parse(jsonMatch[0])
      }
    } catch {}

    return null
  }

  /**
   * Sync current config to avatar bridge
   */
  function syncToAvatar(): void {
    if (!avatarBridge.state.connected) return

    // Convert parameters to morph target format
    const morphTargets: Record<string, number> = {}

    // Body parameters
    for (const [key, value] of Object.entries(config.value.body)) {
      morphTargets[`body_${key}`] = value as number
    }

    // Face parameters
    for (const [key, value] of Object.entries(config.value.face)) {
      morphTargets[`face_${key}`] = value as number
    }

    // Send to avatar
    avatarBridge.sendCommand('morph', {
      morph_targets: morphTargets,
      transition: 0.3
    })
  }

  /**
   * Save current character
   */
  function saveCharacter(name?: string): void {
    const toSave: CharacterConfig = {
      ...config.value,
      name: name || config.value.name,
      updatedAt: Date.now()
    }

    const existing = savedCharacters.value.findIndex(c => c.name === toSave.name)
    if (existing >= 0) {
      savedCharacters.value[existing] = toSave
    } else {
      savedCharacters.value.push(toSave)
    }

    saveSavedCharacters(savedCharacters.value)
  }

  /**
   * Load a saved character
   */
  function loadCharacter(name: string): void {
    const character = savedCharacters.value.find(c => c.name === name)
    if (character) {
      config.value = { ...character }
      syncToAvatar()
      saveConfig(config.value)
    }
  }

  /**
   * Delete a saved character
   */
  function deleteCharacter(name: string): void {
    savedCharacters.value = savedCharacters.value.filter(c => c.name !== name)
    saveSavedCharacters(savedCharacters.value)
  }

  /**
   * Export config as JSON
   */
  function exportConfig(): string {
    return JSON.stringify(config.value, null, 2)
  }

  /**
   * Import config from JSON
   */
  function importConfig(json: string): boolean {
    try {
      const imported = JSON.parse(json)
      if (imported.body && imported.face) {
        config.value = imported
        syncToAvatar()
        saveConfig(config.value)
        return true
      }
    } catch {}
    return false
  }

  /**
   * Generate a description of the current character
   */
  function generateDescription(): string {
    const parts: string[] = []
    const b = config.value.body
    const f = config.value.face

    // Height
    parts.push(heightDisplay.value)

    // Build
    if (b.muscularity > 0.7) parts.push('muscular')
    else if (b.muscularity > 0.5) parts.push('athletic')
    else if (b.muscularity < 0.3) parts.push('slim')

    if (b.bodyFat > 0.6) parts.push('heavyset')
    else if (b.bodyFat < 0.2) parts.push('lean')

    // Features
    if (b.chestSize > 0.7) parts.push('big chest')
    if (b.buttSize > 0.7) parts.push('prominent butt')
    if (b.armSize > 0.7) parts.push('big arms')

    // Anatomy
    if (b.penisLength > 0.7) parts.push('well-endowed')
    if (b.circumcised > 0.5) parts.push('circumcised')
    else parts.push('uncircumcised')

    // Face
    if (f.jawDefinition > 0.7) parts.push('chiseled jaw')
    if (f.beardDensity > 0.5) parts.push('bearded')
    else if (f.stubbleAmount > 0.5) parts.push('scruffy')

    if (f.hairLength < 0.2) parts.push('short hair')
    else if (f.hairLength > 0.7) parts.push('long hair')

    if (f.hairGray > 0.5) parts.push('graying')

    return parts.join(', ')
  }

  // Auto-sync when avatar connects
  watch(() => avatarBridge.state.connected, (connected) => {
    if (connected) {
      syncToAvatar()
    }
  })

  // ========================================================================
  // RETURN
  // ========================================================================

  return {
    // State
    config,
    savedCharacters,
    activeCategory,
    activeSubCategory,
    previewMode,
    showComparison,
    comparisonConfig,

    // Computed
    currentPreset,
    heightDisplay,

    // Categories
    bodyCategories,
    faceCategories,
    parameterLabels,
    presets: PRESETS,

    // Methods
    setBodyParam,
    setFaceParam,
    applyPreset,
    resetToDefaults,
    randomize,
    applyDescription,
    syncToAvatar,
    saveCharacter,
    loadCharacter,
    deleteCharacter,
    exportConfig,
    importConfig,
    generateDescription
  }
}

export type UseCharacterCustomizationReturn = ReturnType<typeof useCharacterCustomization>
