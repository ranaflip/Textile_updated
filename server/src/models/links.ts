import mongoose from 'mongoose';
const LinkSchema = new mongoose.Schema({
  url: { type: String, required: true, unique: true },
  label: String,
  scrapeIntervalSec: { type: Number, default: 300 },
  lastScrapedAt: Date,
});
export default mongoose.model('Link', LinkSchema);