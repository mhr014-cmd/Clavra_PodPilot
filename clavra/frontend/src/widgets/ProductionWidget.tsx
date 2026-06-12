const ProductionWidget = () => {
  return (
    <div className="bg-slate-900 border border-slate-800 rounded-3xl p-6">

      <h2 className="text-2xl font-bold mb-5">
        Production Overview
      </h2>

      <div className="space-y-4">

        {/* Line 1 */}
        <div>
          <div className="flex justify-between mb-2">
            <span>Line 1</span>
            <span>87%</span>
          </div>

          <div className="h-3 bg-slate-800 rounded-full overflow-hidden">
            <div className="h-full w-[87%] bg-blue-500"></div>
          </div>
        </div>

        {/* Line 2 */}
        <div>
          <div className="flex justify-between mb-2">
            <span>Line 2</span>
            <span>72%</span>
          </div>

          <div className="h-3 bg-slate-800 rounded-full overflow-hidden">
            <div className="h-full w-[72%] bg-green-500"></div>
          </div>
        </div>

        {/* Line 3 */}
        <div>
          <div className="flex justify-between mb-2">
            <span>Line 3</span>
            <span>64%</span>
          </div>

          <div className="h-3 bg-slate-800 rounded-full overflow-hidden">
            <div className="h-full w-[64%] bg-orange-500"></div>
          </div>
        </div>

      </div>

    </div>
  )
}

export default ProductionWidget