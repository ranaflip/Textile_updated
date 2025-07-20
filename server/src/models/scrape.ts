import mongoose from 'mongoose';
const ScrapeSchema = new mongoose.Schema({
  linkId: { type: mongoose.Schema.Types.ObjectId, ref: 'Link', required: true },
  title: String,
  description: String,
  price: String,
  currency: String,
  fabricDetails: [{ type: String, composition: String, gsm: String }],
  images: [String],
  scrapedAt: { type: Date, default: Date.now },
});
export default mongoose.model('Scrape', ScrapeSchema);