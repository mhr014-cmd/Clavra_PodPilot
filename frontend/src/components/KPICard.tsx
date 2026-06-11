interface Props {
  title: string;
  value: string;
  growth: string;
}

const KPICard = ({
  title,
  value,
  growth,
}: Props) => {
  return (
    <div className="bg-slate-900 border border-slate-800 rounded-3xl p-6">

      <div className="flex items-center justify-between mb-4">

        <h3 className="text-slate-400 text-lg">
          {title}
        </h3>

        <span className="text-green-400 font-semibold">
          {growth}
        </span>

      </div>

      <div className="text-5xl font-bold text-white">
        {value}
      </div>

    </div>
  );
};

export default KPICard;