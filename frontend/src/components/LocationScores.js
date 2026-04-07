const SCORE_LABELS = {
  global: "Score global",
  transports: "Transports",
  commerces: "Commerces & vie de quartier",
  education: "Éducation",
  sante: "Santé",
  espaces_verts: "Espaces verts",
  calme: "Calme & bruit",
  dynamisme: "Dynamisme immobilier",
};

function ScoreRing({ score, size = 60, label }) {
  const radius = (size - 8) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (score / 100) * circumference;
  const color = score >= 75 ? "#008A00" : score >= 50 ? "#18181B" : "#E60000";

  return (
    <div className="flex items-center gap-4">
      <svg width={size} height={size} className="shrink-0">
        <circle cx={size/2} cy={size/2} r={radius} fill="none" stroke="#e4e4e7" strokeWidth="3" />
        <circle
          cx={size/2} cy={size/2} r={radius} fill="none"
          stroke={color} strokeWidth="3"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          transform={`rotate(-90 ${size/2} ${size/2})`}
          className="score-ring"
          style={{ strokeDashoffset: offset }}
        />
        <text x={size/2} y={size/2} textAnchor="middle" dominantBaseline="central" className="font-mono" fill={color} fontSize="14" fontWeight="600">
          {score}
        </text>
      </svg>
      <div>
        <p className="text-sm font-medium">{label}</p>
        <p className="text-xs text-zinc-400 font-mono">
          {score >= 75 ? "Excellent" : score >= 60 ? "Bon" : score >= 40 ? "Moyen" : "Faible"}
        </p>
      </div>
    </div>
  );
}

export default function LocationScores({ scores }) {
  const globalScore = scores.global || 0;
  const subScores = Object.entries(scores).filter(([k]) => k !== "global");

  return (
    <div data-testid="location-scores">
      <p className="text-xs uppercase tracking-[0.2em] text-zinc-400 font-mono mb-4">Score de localisation</p>

      {/* Global score */}
      <div className="border border-zinc-200 p-6 mb-6">
        <div className="flex items-center gap-6">
          <ScoreRing score={globalScore} size={80} label="Score global" />
          <div className="flex-1">
            <div className="w-full bg-zinc-100 h-2">
              <div className="h-2 bg-black confidence-fill" style={{ width: `${globalScore}%` }} />
            </div>
            <p className="text-xs text-zinc-400 mt-2">
              Composite de {subScores.length} sous-catégories pondérées. Score basé sur la proximité des transports, commerces, écoles, espaces verts et niveau de calme.
            </p>
          </div>
        </div>
      </div>

      {/* Sub-scores grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-px bg-zinc-200">
        {subScores.map(([key, value], i) => (
          <div
            key={key}
            className="bg-white p-6 hover:bg-zinc-50 transition-colors animate-fade-in-up"
            style={{ animationDelay: `${i * 0.06}s` }}
            data-testid={`score-${key}`}
          >
            <ScoreRing score={value} label={SCORE_LABELS[key] || key} />
          </div>
        ))}
      </div>
    </div>
  );
}
