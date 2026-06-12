const ShipmentWidget = () => {
  return (
    <div className="bg-slate-900 border border-slate-800 rounded-3xl p-6">

      <h2 className="text-2xl font-bold mb-5">
        Shipment Status
      </h2>

      <div className="space-y-5">

        {/* Nike */}
        <div className="flex justify-between items-center">
          <div>
            <p className="font-semibold">Nike Order</p>
            <p className="text-slate-400 text-sm">
              Due in 4 days
            </p>
          </div>

          <div className="text-green-400 font-bold">
            Ready
          </div>
        </div>

        {/* H&M */}
        <div className="flex justify-between items-center">
          <div>
            <p className="font-semibold">H&M Order</p>
            <p className="text-slate-400 text-sm">
              Due in 2 days
            </p>
          </div>

          <div className="text-yellow-400 font-bold">
            Risk
          </div>
        </div>

        {/* Puma */}
        <div className="flex justify-between items-center">
          <div>
            <p className="font-semibold">Puma Order</p>
            <p className="text-slate-400 text-sm">
              Delayed
            </p>
          </div>

          <div className="text-red-400 font-bold">
            Delayed
          </div>
        </div>

      </div>

    </div>
  )
}

export default ShipmentWidget